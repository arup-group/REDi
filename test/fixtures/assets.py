import pytest, json

from pathlib import Path

from building import Building, ComponentsLibrary


@pytest.fixture()
def test_building_1():

    path_building = Path('./examples/example_building.json')

    # open the JSON file
    with open(path_building) as f:
        # load the JSON data as a list
        data = json.loads(f.read())
    
    building = Building(building_dict=data)

    yield building



@pytest.fixture()
def test_building_2():

    path_building = Path('./examples/example_building.json')

    # open the JSON file
    with open(path_building) as f:
        # load the JSON data as a list
        data = json.loads(f.read())

    yield data


@pytest.fixture()
def test_component_library_1():

    filepath = Path('./data/components_library.json')

    # open the JSON file
    with open(filepath) as f :

        # load the JSON data 
        components_lib_dict = json.loads(f.read())

        components_lib = ComponentsLibrary(components_lib_dict=components_lib_dict)

    yield components_lib
