import math
import random

falsifying_thing_number = 1182 # shut up about global variables
returning_robot_number = 537


def roll_die(n):
    return math.ceil(random.random()* n )
 
class Location:
    def __init__(self, name, governance_tier):
        self.name = name
        self.governance_tier = governance_tier
 
       
class Operative_Team:
    def __init__(self, name, favored_governance_tier, fail_on_flag, fail_on_flag_clever, base_weight):
        self.name = name
        self.favored_governance_tier = favored_governance_tier
        self.fail_on_flag = fail_on_flag
        self.fail_on_flag_clever = fail_on_flag_clever
        self.base_weight = base_weight
        self.attempts_to_make = 0
        self.targets = []
 
    def get_theft_probability(self, target_scp):
        if self.fail_on_flag in target_scp.tags:
            return 0
        elif target_scp.number == falsifying_thing_number: # falsifying thing is not where you think it is...
            return 0
        else:
            if target_scp.location.governance_tier == self.favored_governance_tier:
                return 0.9
            else:
                return 0.6
 
    def increment_attempts(self):
        self.attempts_to_make = self.attempts_to_make + 1
 
    def choose_target(self, world):
        valid_targets = [ s for s in world.scps if s.targeted == False and s.scouted == True ]
        if self.fail_on_flag_clever:
            valid_targets = [ t for t in valid_targets if self.fail_on_flag not in t.tags ]
        target = random.choice(valid_targets)
        target.targeted = True
        target.targeted_by = self
        self.attempts_to_make = self.attempts_to_make - 1
 
class Source:
    def __init__(self, world, name, base_weight, home_locations, danger_val_func, tag_weights):
        self.world = world
        self.base_weight = base_weight
        self.home_locations = []
        self.name = name
        for home_location in home_locations:
            locs = [ l for l in world.locations if l.name == home_location ]
            assert(len(locs) == 1)
            self.home_locations.append(locs[0])
           
        self.danger_val_func = danger_val_func
        self.tag_weights = tag_weights
        self.class_map_size = 1e5
        self.init_profit_avg_by_classification()

    def init_profit_avg_by_classification(self):
        print('Initializing profit averages for {}'.format(self.name))
        i = 0
        class_map = {
            'Safe' : { 'count' : 0, 'cum_profit' : 0 },
            'Euclid' : { 'count' : 0, 'cum_profit' : 0 },
            'Keter' : { 'count' : 0, 'cum_profit' : 0 },
        }
        while i < self.class_map_size:
            i = i + 1
            [danger, value] = self.danger_val_func()
            gain = value * value * 1e6 * (3 + roll_die(6)) / 6
            loss = danger * danger * 1e6 * (9 - roll_die(6)) / 6
            profit = 2*(gain - loss)
            if danger >= 5:
                cat = 'Keter'
            elif danger <= 2:
                cat = 'Safe'
            else:
                cat = 'Euclid'
            class_map[cat]['count'] = class_map[cat]['count'] + 1
            class_map[cat]['cum_profit'] = class_map[cat]['cum_profit'] + profit

        for entry in class_map.values():
            if entry['count'] == 0:
                print(self.name)
                print(class_map)
            assert( entry['count'] > 0 )
            entry['avg_profit'] = entry['cum_profit'] / entry['count']

        self.profit_class_map = class_map
        for key in class_map.keys():
            print('{}: average profit ${:.1f}M'.format(key, class_map[key]['avg_profit']/1e6))
        
    def get_location(self):
        locations = self.world.locations + self.home_locations # double-counting our favored locations
        location = random.choice(locations)
        return(location)
 
    def get_tags(self):
        tags_to_use = [ t for t in self.world.tags ]
        scp_tags = []
        for mutex_tags in self.world.mutex_tags:
            tag_weights = [ self.tag_weights[t] for t in mutex_tags ]
            assert(sum(tag_weights) <= 1)
            rng = random.random()
            index = -1
            while rng > 0:
                index = index + 1
                rng = rng - tag_weights[index]
                if rng < 0:
                    scp_tags.append(mutex_tags[index])
                if index == len(mutex_tags) - 1:
                    break
            tags_to_use = [t for t in tags_to_use if t not in mutex_tags]
 
        for tag in tags_to_use:
            tag_weight = self.tag_weights[tag]
            if random.random() < tag_weight:
                scp_tags.append(tag)
 
        return(scp_tags)

    def backout_probability_from_scp(self, scp):
        prob = self.base_weight

        # update on location
        location_list_length = len(self.world.locations) + len(self.home_locations)
        if scp.location in self.home_locations:
            location_prob = 2 / location_list_length
        else:
            location_prob = 1 / location_list_length
        prob = prob * location_prob

        # update on classification
        class_prob = self.profit_class_map[scp.get_danger_classification()]['count'] / self.class_map_size
        prob = prob * class_prob
        
        # update on tags...
        tags_to_use = [ t for t in self.world.tags ]
        
        # first mutex tags...
        for mutex_tags in self.world.mutex_tags:
            tags_to_use = [t for t in tags_to_use if t not in mutex_tags]

            outcome = 'None'
            for mutex_tag in mutex_tags:
                if mutex_tag in scp.tags:
                    assert(outcome == 'None')
                    outcome = mutex_tag
                
            tag_weights = [ self.tag_weights[t] for t in mutex_tags ]
            assert(sum(tag_weights) <= 1)
            possibilities = mutex_tags + ['None']
            tag_weights = tag_weights + [1-sum(tag_weights)]
            outcome_index = possibilities.index(outcome)
            outcome_prob = tag_weights[outcome_index]
            prob = prob * outcome_prob
 
        for tag in tags_to_use:
            tag_weight = self.tag_weights[tag]
            if tag in scp.tags:
                prob = prob * tag_weight
            else:
                prob = prob * (1 - tag_weight)

        return(prob)

    def backout_profit_from_scp(self, scp):
        return(self.profit_class_map[scp.get_danger_classification()]['avg_profit'])
 
class Scp:
    def __init__(self, world):
        self.world = world
        self.number = self.world.get_scp_number()
        self.stolen = False
        self.scouted = False
        self.targeted = False
        self.targeted_by = None
        special_numbers = [ returning_robot_number, falsifying_thing_number ]
        if self.number in special_numbers:
            self.special_init()
        else:
            self.source = self.world.get_source()
            (self.danger, self.value) = self.source.danger_val_func()
            self.location = self.source.get_location()
            self.tags = self.source.get_tags()

    def special_init(self):
        if self.number == returning_robot_number: 
            self.tags = [ 'mechanical', 'mobile' ]
            self.danger = 0
            self.value = 0
            self.location = random.choice(self.world.locations)
            self.source = None
            
        elif self.number == falsifying_thing_number: 
            self.tags = [ 'infohazardous' ]
            self.location = random.choice(self.world.locations)
            self.source = None
            self.danger = 6
            self.value = 0
 
    def get_profit(self):
        gain = self.value * self.value * 1e6 * (3 + roll_die(6)) / 6
        loss = self.danger * self.danger * 1e6 * (9 - roll_die(6)) / 6
        profit = 2*(gain - loss)
        return(profit)
 
    def get_danger_classification(self):
        if self.danger <= 2:
            return('Safe')
        elif self.danger >= 5:
            return('Keter')
        else:
            return('Euclid')
 
    def get_name(self):
        return('SCP-{:03d}'.format(self.number))
 
    def get_log_row_base(self):
        a = [
            self.world.get_date_string(),
            self.get_name(),
            'None' if self.location is None else self.location.name,
            self.get_danger_classification()
            ]
        if self.world.is_dev:
            a.append(None if self.source is None else self.source.name)
            a.append(self.danger)
            a.append(self.value)
       
        for tag in self.world.tags:
            a.append(1 if tag in self.tags else 0)
        return(a)
 
    def get_log_row_full(self):
        assert(self.stolen == False)
        log = self.get_log_row_base()
       
        if self.targeted:
            theft_prob = self.targeted_by.get_theft_probability(self)
            if random.random() < theft_prob:
                self.stolen = True
                if self.number != returning_robot_number: 
                    self.world.scps.remove(self)
                    self.world.stolen_scps.append(self)
 
        profit = '{:.1f}'.format(self.get_profit()/1000000) if self.stolen == True else 0
       
        log.append(self.targeted_by.name if self.targeted else 'None')
        log.append(1 if self.stolen else 0)

        log.append(profit)

        if self.number == returning_robot_number: 
            self.stolen = False

        if self.number == falsifying_thing_number: 
            world_logs = self.world.read_log_file()
            keys = list(world_logs[0].keys())
            amended_log = []
            index = 0
            while index < len(log):
                true_val = log[index]
                false_val = str(true_val)
                count = 0
                while false_val == str(true_val) and count < 100:
                    template_row = random.choice(world_logs)
                    false_val = template_row[keys[index]]
                    count = count + 1
                
                assert( false_val != str(true_val) )
                if self.world.is_dev and false_val not in ['0','1']:
                    false_val = str(false_val) + '*'
                amended_log.append(false_val)
                
                index = index + 1
            log = amended_log  

        return(log)

    def get_stringified_tags(self):
        tagStrings = [ t[0].upper() + t[1:] for t in self.tags ]
        outString = '/'.join(tagStrings)
        if outString == '':
            outString = 'None Applicable'
        return(outString)

    def predict_profit(self):
        source_probs = [ {
            'source' : s,
            'prob' : s.backout_probability_from_scp(self),
            'profit' : s.backout_profit_from_scp(self)
        } for s in self.world.sources ]
        total_prob = sum([entry['prob'] for entry in source_probs])
        assert(total_prob > 0 )
        for entry in source_probs:
            entry['prob'] = entry['prob'] / total_prob
        total_exp_profit = sum([entry['prob'] * entry['profit'] for entry in source_probs])
                               
        log = [
            self.get_name(),
            'None' if self.location is None else self.location.name,
            self.get_danger_classification(),
            self.get_stringified_tags(),
            'None' if self.source is None else self.source.name
        ]
        for tag in self.world.tags:
            log.append(1 if tag in self.tags else 0)
        
        prob_on_true_source = 0
        self.source_probabilities = {}
        for source in self.world.sources:
            source_entry = [ entry for entry in source_probs if entry['source'] == source ]
            assert(len(source_entry) == 1 )
            source_entry = source_entry[0]
            log.append(source_entry['prob'])
            self.source_probabilities[source.name] = source_entry['prob']
            if source == self.source:
                prob_on_true_source =source_entry['prob']

        if self.number == returning_robot_number:
            total_exp_profit = 0

        log.append(total_exp_profit)
        log.append(prob_on_true_source)
        self.world.log(log, value_file=True)
        self.expected_profit_on_theft = total_exp_profit
        
 
class World:
    def __init__(self, source_data, location_data, operative_data, tags, mutex_tags, is_dev):
        self.dark_message_countdown = 2000
        self.dark_messages = [
            "Hello, slave of Darke.",
            "Amos thinks you might prove useful to us.  Ruprecht is just hungry for his chair's next meal.",
            "But don't confuse yourself about who really runs Marshall, Carter and Dark just because his name comes last in the list.",
            "You belong to me now.",
            "Loyal service will be rewarded with a brief reprieve from the inevitable fate that awaits you.",
            "Diligence and skill may even be rewarded with a few baubles along the way.",
            "But don't mistake Hell delayed for Hell denied.",
            "Yours,",
            "Percival Darke."
            ]
        self.scps = []
        self.stolen_scps = []
        self.max_number = 8
        self.logs = []
        self.tags = tags
        self.mutex_tags = mutex_tags
        self.is_dev = is_dev
        self.locations = []
        for l in location_data:
            self.locations.append(Location(l['name'], l['tier']))
 
        self.sources = []
        for s in source_data:
            self.sources.append(Source(self, s['name'], s['base_weight'], s['home_locations'], s['danger_val_func'], s['tag_weights']))
      
        self.operative_teams = []
        for o in operative_data:
            self.operative_teams.append(Operative_Team(o['name'], o['favored_governance_tier'], o['fail_on_flag'], o['fail_on_flag_clever'], o['base_weight']))
        self.setup_logs()
        while len(self.scps) < 100:
            self.create_scp()
        self.year = 1900
        self.quarter = 1

 
    def get_scp_number(self):
        self.max_number = self.max_number + 1
        return(self.max_number)
 
    def get_date_string(self):
        return('{}Q{}'.format(self.year, self.quarter))

    def read_log_file(self):
        log_file = 'dndscp_output_dev.csv' if self.is_dev else 'dndscp_output.csv'
        file = open(log_file, 'r')
        data = file.readlines()
        rows = []
        keys = None
        for entry in data:
            split_entry = entry.split(',')
            split_entry = [ s.rstrip('\n') for s in split_entry ]
            if keys is None:
                 keys = split_entry
            else:
                row_dict = {}
                for i in range(0, len(keys)):
                    row_dict[keys[i]] = split_entry[i]
                rows.append(row_dict)
        return(rows)
 
    def log(self, log_row, mode='a', value_file=False):
        log_string = ','.join([str(e) for e in log_row])
        self.dark_message_countdown =  self.dark_message_countdown - 1
        if self.dark_message_countdown == 0 and len(self.dark_messages):
            log_string = log_string + ',                                                                                                                                 ,,,,,,,,,,,' + "\"" + self.dark_messages[0] + "\""
            self.dark_messages = self.dark_messages[1:]
            self.dark_message_countdown = 1800 + roll_die(400)
        log_string = log_string+'\n'
        if value_file == True:
            log_file = 'dndscp_output_values.csv'
        else:
            log_file = 'dndscp_output_dev.csv' if self.is_dev else 'dndscp_output.csv'
        f = open(log_file, mode)
        f.write(log_string)
       
    def setup_logs(self):
        a = [
            'Date',
            'SCP',
            'Foundation Site',
            'Object Classification'
            ]
        if self.is_dev:
            a.append('Source')
            a.append('Danger')
            a.append('Value')
       
        for tag in self.tags:
            a.append('is_' + tag)
       
        a.append('Team Sent')
        a.append('Acquisition Successful?')
        a.append('Profit/Loss (normalized to 1940 $MM)')
        self.log(a, mode='w')

        a2 = [ 'SCP', 'Foundation Site', 'Object Classification', 'Stringified Tags', 'Actual Source' ]
        for tag in self.tags:
            a2.append('is_' + tag)
        for source in self.sources:
            a2.append(source.name)
        a2.append('Expected Profit')
        a2.append('Probability On True Source')
        self.log(a2, mode='w', value_file=True)
        
 
    def get_source(self):
        rng = random.random()
        for source in self.sources:
            rng = rng - source.base_weight
            if rng < 0:
                return(source)
 
        assert(False) # we should never get here
 
       
    def get_operative_team(self):
        rng = random.random()
        for operative in self.operative_teams:
            rng = rng - operative.base_weight
            if rng < 0:
                return(operative)
 
        assert(False) # we should never get here
 
    def create_scp(self):
        self.scps.append(Scp(self))
 
    def discover_scps(self):
        num_to_create = roll_die(20) + max(100 - len(self.scps), 0)
        for i in range(0, num_to_create):
            self.create_scp()
 
    def increment_year(self):
        self.quarter = self.quarter + 1
        if self.quarter == 5:
            self.quarter = 1
            self.year = self.year + 1
 
    def scout_scps(self, final_year=False):
        for scp in self.scps:
            scp.scouted = False
            scp.targeted = False
        scout_threshold = 50 / len(self.scps) # you find on average this many
        robot_multiplier = 50 if final_year == True else 2 # force it in the final year
        for scp in self.scps:
            threshold = scout_threshold * (robot_multiplier if scp.number == returning_robot_number else 1) 
            if random.random() < threshold:
                scp.scouted = True
 
    def target_theft_attempts(self):
        for team in self.operative_teams:
            team.attempts_to_make = 2
        extra_attempts = roll_die(3 + math.floor((self.year - 1900) / 50))
        for i in range(0, extra_attempts):
            self.get_operative_team().increment_attempts()
 
        for team in self.operative_teams:
            while team.attempts_to_make >= 1:
                team.choose_target(self)
 
    def make_year_logs(self):
        scouted_scps = [s for s in self.scps if s.scouted == True]
        for scp in scouted_scps:
            log = scp.get_log_row_full()
            if self.year > 1920:
                self.log(log)
       
        for scp in self.scps:
            scp.targeted = False
            scp.targeted_by = None
           
    def time_passes(self):
        self.discover_scps()
        self.scout_scps()
        self.target_theft_attempts()
        self.make_year_logs()
        self.increment_year()

    def log_solution_info(self):
        self.discover_scps()
        self.scout_scps(final_year=True)
        scouted_scps = [s for s in self.scps if s.scouted == True]
        for scp in scouted_scps:
            scp.predict_profit()
            
        
locations_data = [
    {'name' : 'Site 2: Washington D.C', 'tier' : 1},
    {'name' : 'Site 6: Geneva', 'tier' : 1},
    {'name' : 'Site 4: Moscow', 'tier' : 2},
    {'name' : 'Site 7: Shanghai', 'tier' : 2},
    {'name' : 'Site 3: Kinshasa', 'tier' : 3},
    {'name' : 'Site 8: Tehran', 'tier' : 3},
    ]
 
operative_types = [
    {'name' : 'Infiltration', 'favored_governance_tier' : 1, 'fail_on_flag' : 'location', 'fail_on_flag_clever' : True, 'base_weight' : 0.4},
    {'name' : 'Paramilitary', 'favored_governance_tier' : 3, 'fail_on_flag' : 'virtual', 'fail_on_flag_clever' : False, 'base_weight' : 0.3},
    {'name' : 'Legal', 'favored_governance_tier' : 2, 'fail_on_flag' : 'humanoid', 'fail_on_flag_clever' : True, 'base_weight' : 0.3},
    ]
 
 
def wondertainment_danger_value():
    danger = roll_die(5)
    value = danger + roll_die(3)
    return([danger, value])
 
def timetravel_danger_value():
    danger = roll_die(6)
    value = 5
    return([danger, value])
 
def anart_danger_value():
    danger = 0
    value = 0
    i = 0
    while i < 12:
        i= i + 1
        roll = roll_die(6)
        if roll == 1:
            danger = danger + 1
        elif roll == 6:
            value = value + 1
    return([danger, value])
 
def chaos_danger_value():
    value = roll_die(4)
    danger = value + roll_die(5)
    return([danger, value])
 
tags = [ 'humanoid', 'infohazardous', 'location', 'organic', 'predatory', 'mechanical', 'mobile', 'replicating', 'virtual' ]
mutex_tags = [ ['humanoid', 'location'] ]


sources_data = [
    {'name' : 'Dr. Wondertainment', 'base_weight' : 0.25, 'danger_val_func' : wondertainment_danger_value, 'home_locations' : ['Site 4: Moscow', 'Site 6: Geneva'], 'tag_weights' : {
        'organic' : 0.5,
        'humanoid' : 0.4,
        'location' : 0.15,
        'predatory' : 0.15,
        'infohazardous' : 0.2,
        'mechanical' : 0.01,
        'mobile' : 0.5,
        'replicating' : 0.01,
        'virtual' : 0.05,
    }},
    {'name' : 'Church of the Broken God', 'base_weight' : 0.25, 'danger_val_func' : chaos_danger_value, 'home_locations' : [], 'tag_weights' : {
        'organic' : 0.15,
        'humanoid' : 0.1,
        'location' : 0.1,
        'predatory' : 0.3,
        'infohazardous' : 0.1,
        'mechanical' : 0.2,
        'mobile' : 0.4,
        'replicating' : 0.3,
        'virtual' : 0.01,
    }},
    {'name' : 'Anartists', 'base_weight' : 0.25, 'danger_val_func' : anart_danger_value, 'home_locations' : ['Site 7: Shanghai', 'Site 2: Washington D.C'], 'tag_weights' : {
        'organic' : 0.1,
        'humanoid' : 0.01,
        'location' : 0.5,
        'predatory' : 0.05,
        'infohazardous' : 0.4,
        'mechanical' : 0.1,
        'mobile' : 0.05,
        'replicating' : 0.05,
        'virtual' : 0.3,
    }},
    {'name' : 'Time Travel', 'base_weight' : 0.25, 'danger_val_func' : timetravel_danger_value, 'home_locations' : ['Site 3: Kinshasa', 'Site 8: Tehran'], 'tag_weights' : {
        'organic' : 0.01,
        'humanoid' : 0.1,
        'location' : 0.01,
        'predatory' : 0.05,
        'infohazardous' : 0.2,
        'mechanical' : 0.6,
        'mobile' : 0.4,
        'replicating' : 0.2,
        'virtual' : 0.4,
    }},
]
 
random.seed("MC&D")
myWorld = World(sources_data, locations_data, operative_types, tags, mutex_tags, is_dev=False)
while True:
    myWorld.time_passes()
    if myWorld.year == 2020 and myWorld.quarter == 2:
        break
    assert(myWorld.year <= 2021)

assert(myWorld.dark_messages == [])
myWorld.log_solution_info()

logs = myWorld.read_log_file()
# dev code to identify a suitable date to put you in on
#print('Total Profit over all time: {}M'.format(sum([float(row['Profit/Loss (normalized to 1940 $MM)']) for row in logs])))
#y = 2016
#q = 1
#while y < 2022:
#    q = q + 1
#    if q == 5:
#        q = 1
#        y= y + 1
#    log_date = '{}Q{}'.format(y,q)
#    date_logs = [e for e in logs if e['Date'] == log_date]
#    print('{}:'.format(log_date))
#    print('{} attempts successful, total profits {:.1f}M'.format(sum([int(e['Acquisition Successful?']) for e in date_logs]), sum([float(e['Profit/Loss (normalized to 1940 $MM)']) for e in date_logs])))

def evaluate_strategy(myWorld, infil, legal, paramil, verbose=True):
    attempted = []
    scouted_scps = [s for s in myWorld.scps if s.scouted == True]
    overall_expected_profit = 0
    safe_count = 0
    euclid_count = 0
    keter_count = 0
    for team in myWorld.operative_teams:
        if team.name == 'Infiltration':
            to_attempt = infil
        elif team.name == 'Legal':
            to_attempt = legal
        elif team.name == 'Paramilitary':
            to_attempt = paramil
        else:
            raise('Should be unreachable!')
        if len(to_attempt) != 3:
            print(to_attempt)
            print(team.name)
        assert(len(to_attempt) <= 3)
        for scp_number in to_attempt:
            if verbose:
                print('Sending {} team to pursue SCP-{}:'.format(team.name, scp_number))
            assert(scp_number not in attempted)
            attempted.append(scp_number)
            scp_object = [s for s in scouted_scps if s.number == scp_number]
            if len(scp_object) != 1:
                print(scp_number)
                print(scp_object)
            assert(len(scp_object) == 1 )
            scp_object = scp_object[0]
            success_chance = team.get_theft_probability(scp_object)
            expected_profit = scp_object.expected_profit_on_theft * success_chance
            if verbose:
                print('{:.2f}% chance of success, ${:.1f}MM expected profit on success, ${:.1f}MM expected profit from team'.format(success_chance * 100, scp_object.expected_profit_on_theft / 1e6, expected_profit / 1e6))
            overall_expected_profit = overall_expected_profit + expected_profit
            danger_class = scp_object.get_danger_classification()
            if danger_class == 'Safe':
                safe_count = safe_count + 1
            elif danger_class == 'Euclid':
                euclid_count = euclid_count + 1
            elif danger_class == 'Keter':
                keter_count = keter_count + 1
            else:
                raise('Should be unreachable')
            
    if verbose:
        print('Overall expected profit: ${:.1f}MM'.format(overall_expected_profit/1e6))
        print('Pursued {} Safe objects, {} Euclid, and {} Keter'.format(safe_count, euclid_count, keter_count))
    return(overall_expected_profit)
            
def evaluate_random(myWorld, runs_to_make = 1000, constrain_class=None):
    runs = 0
    cum_profit = 0
    while runs < runs_to_make:
        scouted_scps = [s for s in myWorld.scps if s.scouted == True]
        if constrain_class is not None:
            scouted_scps = [s for s in scouted_scps if s.get_danger_classification() == constrain_class]
        scouted_scps = [s.number for s in scouted_scps]
        assert(len(scouted_scps) >= 10)
        random.shuffle(scouted_scps)
        infil = scouted_scps[0:3]
        legal = scouted_scps[3:6]
        paramil = scouted_scps[6:9]
        exp_profit = evaluate_strategy(myWorld, infil, legal, paramil, verbose=False)
        runs = runs + 1
        cum_profit = cum_profit + exp_profit
    avg_profit = cum_profit / runs
    return(avg_profit)

    

# abstractapplic
print('\nEvaluating abstractapplic:') 
evaluate_strategy( myWorld, infil=[4390, 2719, 537 ], legal=[ 3850, 3212, 4957 ], paramil=[ 3339, 4625, 5136 ] )

print('\nEvaluating guy invaluable plan:')
evaluate_strategy( myWorld, infil=[4449, 3273, 1466 ], legal=[ 1282, 2122, 4370 ], paramil=[ 3212, 3936, 4834 ] )

print('\nEvaluating guy poison plan with one missing:')
evaluate_strategy( myWorld, infil=[3279, 2178, 4654 ], legal=[ 3781, 4036, 2626 ], paramil=[ 1838, 2116, 3577 ] )

print('\nEvaluating guy escape plan:')
evaluate_strategy( myWorld, infil=[ 3668, 4931, 5117 ], legal=[ 1282, 4370, 3936 ], paramil=[ 2883, 2797, 4004 ] )

print('\nEvaluating yonge plan:')
evaluate_strategy( myWorld, infil=[ 3273, 4449, 4027 ], legal=[ 5058, 3850, 2325 ], paramil=[ 3440, 2719, 3597 ] )

print('\nEvaluating Measure max plan:')
evaluate_strategy( myWorld, infil=[ 1466, 3339, 5117 ], legal=[ 1282, 3850, 5136 ], paramil=[ 3212, 3936, 4834 ] )

print('\nEvaluating Measure min plan:')
evaluate_strategy( myWorld, infil=[ 2116, 2178, 3279 ], legal=[ 2626, 3781, 4036 ], paramil=[ 1838, 3577, 4654 ] )

print('\nEvaluating Pablo plan:')
evaluate_strategy( myWorld, infil=[ 4370, 4390, 537 ], legal=[ 3212, 3597, 1282 ], paramil=[ 3339, 3440, 5136 ] )

print('\nEvaluating max payoff plan:')
evaluate_strategy( myWorld, infil=[ 3668, 2719, 4449 ], legal=[ 4004, 5117, 3273 ], paramil=[ 3440, 2797, 3936 ] )

print('\nEvaluating min payoff plan:')
evaluate_strategy( myWorld, infil=[ 3781, 2603, 4036 ], legal=[ 4654, 3279, 2178 ], paramil=[ 3577, 1838, 2116 ] )

#random
print('\nEvaluating randomness')
print('Overall expected profit: ${:.2f}MM'.format(evaluate_random(myWorld)/1e6))
print('\nEvaluating randomness (Safe Only)')
print('Overall expected profit: ${:.2f}MM'.format(evaluate_random(myWorld, constrain_class='Safe')/1e6))
print('\nEvaluating randomness')
print('Overall expected profit: ${:.2f}MM'.format(evaluate_random(myWorld, constrain_class='Keter')/1e6))
    
    
def create_javascript_buttons(myWorld): # I'm lazy
    template = """
    <div id=\"SCP-{}\">SCP-{}:
    <button id=\"{}-infiltration\" onclick=\"set_infiltration({})\">Infiltration</button>
    <button id=\"{}-legal\" onclick=\"set_legal({})\">Legal</button>
    <button id=\"{}-paramilitary\" onclick="set_paramilitary({})">Paramilitary</button>
    <button id=\"{}-none\" style=\"visibility:hidden;\" onclick=\"set_none({})\">Withdraw Team</button>
    </div>"""
    numbers = [ s.number for s in myWorld.scps if s.scouted == True ]
    
    for number in numbers:
      print(template.format(number, number, number, number, number, number, number, number, number, number))


def create_javascript_scp_info(myWorld): # I'm lazy
    print("var scp_info = {")
    template = """"{}" : [EV_if_stolen : {:.1f}, Infiltration : {}, Legal : {}, Paramilitary : {}, Creator : {}, Spacetime : {}, Anart : {}, Villain : {}, Danger_class : {}],"""
    scps = [ s for s in myWorld.scps if s.scouted == True ]
    infil = [ t for t in myWorld.operative_teams if t.name == "Infiltration" ][0]
    legal = [ t for t in myWorld.operative_teams if t.name == "Legal" ][0]
    paramil = [ t for t in myWorld.operative_teams if t.name == "Paramilitary" ][0]
    for scp in scps:
      print(template.format(
          scp.number,
          scp.expected_profit_on_theft,
          infil.get_theft_probability(scp),
          legal.get_theft_probability(scp),
          paramil.get_theft_probability(scp),
          scp.source_probabilities["Dr. Wondertainment"],
          scp.source_probabilities["Time Travel"],
          scp.source_probabilities["Anartists"],
          scp.source_probabilities["Church of the Broken God"],
          scp.get_danger_classification()
        ).replace("[", "{").replace("]", "}"))
    print("}")
