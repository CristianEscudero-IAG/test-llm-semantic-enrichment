import pickle

def load_pickle(filename="data/iberia/parsed_list.pkl"):
    with open(filename, "rb") as f:
        parsed_list = pickle.load(f)
    return parsed_list

def write_to_pickle(parsed_list, filename="data/iberia/parsed_list.pkl"):
    with open(filename, 'wb') as f:
            pickle.dump(parsed_list, f)