import pytest
import pytest_mock
from itertools import product, cycle
from copy import deepcopy

import numpy as np

from pyplate import Container, Substance, Unit, config

from .unit_test_constants import epsilon, \
                            test_names, \
                            test_whitespace_patterns, \
                            test_non_parseable_quantities, \
                            test_invalid_values, \
                            test_base_units, \
                            test_prefixes, \
                            test_prefix_multipliers, \
                            test_units, \
                            test_invalid_units, \
                            test_volume_units, \
                            test_positive_volumes, \
                            test_negative_volumes, \
                            test_zero_volumes, \
                            test_negative_quantities

from .common_mock_functions import mock_parse_quantity, mock_parse_concentration

def test_Container___init__(water, salt):
    """
    Unit test for the `Container` constructor.

    This unit test checks the following scenarios:
    - Arguments raise a `TypeError` if they are not the correct types.
    - Arguments raise a `ValueError` if their values fail to satisfy the 
      required constraints.
    - Container properties are correctly initialized for the cases of:
        1. Only 'name' provided
        2. 'name' and 'max_volume' provided
        3. 'name' and 'initial_contents' provided
        4. 'name', 'max_volume', and 'initial_contents' provided

    NOTE: More rigorous tests of the initial_contents variations are tested in
    the unit test for `Container._set_initial_contents()`.
    """

    # ==========================================================================
    # Failure Case: Invalid argument types
    # ==========================================================================

    # NOTE: Argument 'initial_contents' is not tested here, as it is tested in
    # the unit test for Container._set_initial_contents()

    for non_str in [None, False, 1, 1.0, [], {}]:
        with pytest.raises(TypeError, match="Name must be a str"):
            Container(non_str)
    
    for non_str in [None, False, 1, 1.0, [], ['1 mL'], {}]:
        with pytest.raises(TypeError, match='Maximum volume must be a str'):
            Container('container', non_str)


    # ==========================================================================
    # Failure Case: Empty name
    # ==========================================================================

    with pytest.raises(ValueError, match="Name must not be empty"):
        Container('')


    # ==========================================================================
    # Failure Case: Names with only whitespace
    # ==========================================================================

    for test_name in test_whitespace_patterns:
        merged_test_name = test_name.replace('e', '')
        if merged_test_name != '':
            error_msg = "Name must contain non-whitespace characters."
            with pytest.raises(ValueError, match=error_msg):
                Container(merged_test_name)
    

    # ==========================================================================
    # Failure Case: Maximum volume is not formatted as 'value unit'
    # ==========================================================================
    # 
    # NOTE: This is really a failure case for Unit.parse_quantity(), not 
    # for constructing Containers. However, it is still worth checking here
    # in case the call to Unit.parse_quantity() is not correctly implemented
    # in the constructor for Container. The error type and message are not 
    # checked here, as that would further couple this test to the implementation
    # details of Unit.parse_quantity(). 

    for test_quantity in test_non_parseable_quantities:
        for pattern in test_whitespace_patterns:
            merged_test_quantity = pattern.replace('e', test_quantity)
            with pytest.raises(Exception):
                Container('container', merged_test_quantity)

    # ==========================================================================
    # Failure Case: Maximum volume 'value' cannot be parsed as a float
    # ==========================================================================
    #
    # NOTE: This is really a failure case for Unit.parse_quantity(), not 
    # for constructing Containers. However, it is still worth checking here
    # in case the call to Unit.parse_quantity() is not correctly implemented
    # in the constructor for Container. The error type and message are not 
    # checked here, as that would further couple this test to the implementation
    # details of Unit.parse_quantity(). 

    for test_value in test_invalid_values:
        for unit in test_volume_units:
            test_volume = test_value + ' ' + unit
            for pattern in test_whitespace_patterns:
                merged_test_value = pattern.replace('e', test_volume)
                with pytest.raises(Exception):
                    Container('container', merged_test_value)

    # ==========================================================================
    # Failure Case: Maximum volume 'unit' is not a valid unit
    # ==========================================================================
    #
    # NOTE: This is really a failure case for Unit.parse_quantity(), not 
    # for constructing Containers. However, it is still worth checking here
    # in case the call to Unit.parse_quantity() is not correctly implemented
    # in the constructor for Container. The error type and message are not 
    # checked here, as that would further couple this test to the implementation
    # details of Unit.parse_quantity(). 

    for unit in test_invalid_units:
        for pattern in test_whitespace_patterns:
            merged_test_value = pattern.replace('e', '10 ' + unit)
            with pytest.raises(Exception):
                Container('container', merged_test_value)
                

    # ==========================================================================
    # Failure Case: Maximum volume 'unit' does not represent volume
    # ==========================================================================
    #
    # Variations for test quantities include:
    # - Moles (base unit)
    # - Grams (base unit)
    # - Mircomoles (prefixed unit)
    # - Kilograms (prefixed unit)

    test_units = ['mol', 'g', 'umol', 'kg']
    for test_unit in test_units:
        for pattern in test_whitespace_patterns:
            # NOTE: The parentheses and periods are special characters for regular
            # expression patterns, so they need to be escaped.
            with pytest.raises(ValueError, match="Maximum volume must have volume " + \
                                                "units \\(e\\.g\\. L, mL, uL, etc\\.\\)\\."):
                Container('container', pattern.replace('e','100 ' + test_unit))


    # ==========================================================================
    # Failure Case: Maximum volume is non-positive
    # ==========================================================================
    
    for test_volume in test_negative_volumes:
        for pattern in test_whitespace_patterns:
            with pytest.raises(ValueError, match="Maximum volume must be positive"):
                Container('container', pattern.replace('e',test_volume))

    for test_volume in test_zero_volumes:
        for pattern in test_whitespace_patterns:
            with pytest.raises(ValueError, match="Maximum volume must be positive"):
                Container('container', pattern.replace('e',test_volume))


    # ==========================================================================
    # Failure Case: Maximum volume is NaN
    # ==========================================================================
    
    for pattern in test_whitespace_patterns:
        with pytest.raises(ValueError, match="'NaN' values are forbidden for quantities\\."):
            Container('container', pattern.replace('e','nan L'))


    # ==========================================================================
    # Success Case: Only name provided
    # ==========================================================================

    for test_name in test_names:
        for pattern in test_whitespace_patterns:
            merged_test_name = pattern.replace('e', test_name)
            test_container = Container(merged_test_name)

            # Check for correct name, max_volume, and initial contents
            assert test_container.name == merged_test_name, \
                "Container 'name' attribute does not match 'name' constructor argument."
            assert test_container.max_volume == float('inf'), \
                "Container 'max_volume' attribute does not match 'max_volume' default constructor argument."
            assert len(test_container.contents) == 0, \
                "Container 'contents' attribute does not match 'initial_contents' default constructor argument."
    

    # ==========================================================================
    # Success Case: name and max_volume provided
    # ==========================================================================
    
    # Pre-compute parsed quantities to save time
    parsed_test_volumes = map(Unit.parse_quantity, test_positive_volumes)

    for test_name in test_names:
        for test_volume, (test_value, test_unit) in zip(test_positive_volumes, 
                                                        parsed_test_volumes):
            test_container = Container(test_name, test_volume)

            # Check for correct name, max_volume, and initial contents
            assert test_container.name == test_name, \
                "Container 'name' attribute does not match 'name' constructor argument."
            assert test_container.max_volume == Unit.convert_to_storage(test_value, test_unit), \
                "Container 'max_volume' attribute does not match 'max_volume' constructor argument."
            assert len(test_container.contents) == 0, \
                "Container 'contents' attribute does not match 'initial_contents' default constructor argument."
    

    # ==========================================================================
    # Success Case: name and initial_contents are provided
    # ==========================================================================

    # TODO: Ideally improve the variations here, and possibly move to 
    # test constants
    test_initial_contents = [[(water, '1 mol')],
                             [(water, '1 g')],
                             [(water, '1 L')],
                             [(salt, '10 g')],
                             [(salt, '10 mol')],
                             [(salt, '10 L')],
                             [(water, '5 L'), (salt, '0.48 mol')]
                            ]

    for test_name in test_names:
        for initial_contents in test_initial_contents:
            test_container = Container(test_name, initial_contents=initial_contents)              
                
            # Check for correct name and max_volume
            assert test_container.name == test_name, \
                "Container 'name' attribute does not match 'name' constructor argument."
            assert test_container.max_volume == float('inf'), \
                "Container 'max_volume' attribute does not match 'max_volume' default constructor argument."
            
            # Check that the size of the container contents matches that of the specified 
            # initial_contents
            assert len(test_container.contents) == len(initial_contents), \
                "Container 'contents' attribute does have the same size as 'initial_contents' constructor argument."
            
            # Check that each substance in initial_contents is in Container contents,
            # and check that the amount matches the amount specified
            for substance, quantity in initial_contents:
                assert substance in test_container.contents, \
                    f"Container 'contents' is missing substance '{substance}' that was present in" + \
                    " 'initial_contents' constructor argument."
                
                # NOTE: This line creates an interdependence between unit tests. 
                # If Substance.convert_quantity() is not working, this test will not work correctly.
                umols_substance = substance.convert_quantity(quantity, config.moles_storage_unit)
                assert test_container.contents[substance] == pytest.approx(umols_substance)


    # ==========================================================================
    # Success Case: name, max_volume, and initial_contents are provided
    # ==========================================================================

    for test_name in test_names:
        for test_volume, (test_value, test_unit) in zip(test_positive_volumes, 
                                                        parsed_test_volumes):
            for initial_contents in test_initial_contents:
                test_container = Container(test_name, initial_contents=initial_contents)              
                    
                # Check for correct name
                assert test_container.name == test_name, \
                    "Container 'name' attribute does not match 'name' constructor argument."
                
                # Check for correct max_volume
                assert test_container.max_volume == Unit.convert_to_storage(test_value, test_unit), \
                    "Container 'max_volume' attribute does not match 'max_volume' constructor argument."
                
                # Check that the size of the container contents matches that of the specified 
                # initial_contents
                assert len(test_container.contents) == len(initial_contents), \
                    "Container 'contents' attribute does have the same size as 'initial_contents' constructor argument."
                
                # Check that each substance in initial_contents is in Container contents,
                # and check that the amount matches the amount specified
                for substance, quantity in initial_contents:
                    assert substance in test_container.contents, \
                        f"Container 'contents' is missing substance '{substance}' that was present in" + \
                        " 'initial_contents' constructor argument."
                    
                    # NOTE: This line creates an interdependence between unit tests. 
                    # If Substance.convert_quantity() is not working, this test will not work correctly.
                    umols_substance = substance.convert_quantity(quantity, config.moles_storage_unit)
                    assert test_container.contents[substance] == pytest.approx(umols_substance)

def test_Container___eq__(empty_container, empty_plate, water, dmso):
    """
    Unit Test for the function `Container.__eq__()`

    This test checks the following scenarios:
    - Comparison between a Container and a non-container second argument
    - Comparison between a Container and itself
    - Comparison between two identical empty containers
    - Comparison between two identical non-empty containers
    - Comparison between two containers which are identical except for each of
      the following attributes:
      - Name
      - Max Volume
      - Current Volume
      - Contents (multiple variations tested)
    """

    # ==========================================================================
    # False Case: Non-container second argument
    # ==========================================================================
    for non_container in [None, False, 1, "str", 
                        [empty_container], [empty_container, empty_container],
                        (empty_container,), (empty_container, empty_container),
                        {"0": empty_container},
                        empty_plate]:
        assert not (empty_container == non_container), \
            f"Non-container object treated as equal! Object: {type(non_container)}"


    # Create an empty container with the same name as the 'empty_container'
    # fixture for test cases that follow
    test_container_empty = Container(empty_container.name)


    # ==========================================================================
    # True Case: First and second arguments are the same Python object
    # ==========================================================================
    assert empty_container == empty_container


    # ==========================================================================
    # True Case: First and second arguments are identical empty containers
    # ==========================================================================
    assert empty_container == test_container_empty


    # Create non-empty containers for test cases that follow
    test_container_water_1 = Container('water_stock', '10 mL', 
                                       initial_contents=[(water, '10 mL')])
    test_container_water_2 = Container('water_stock', '10 mL', 
                                       initial_contents=[(water, '10 mL')])

    # ==========================================================================
    # True Case: First and second arguments are dentical non-empty containers
    # ==========================================================================
    assert test_container_water_1 == test_container_water_2


    # ==========================================================================
    # False Case: First and second arguments have different names
    # ==========================================================================
    test_container_water_1.name = "water_solution"
    assert not (test_container_water_1 == test_container_water_2)
    # Reset name for future tests
    test_container_water_1.name = test_container_water_2.name


    # ==========================================================================
    # False Case: First and second arguments have different maximum volumes
    #             (both finite and infinite volumes are tested)
    # ==========================================================================

    # Test finite amounts for both containers
    test_container_water_1.max_volume = 20
    assert not (test_container_water_1 == test_container_water_2)

    # Test infinite maximum volume for one container and finite maximum volume
    # for the other container
    test_container_water_1.max_volume = float('inf')
    assert not (test_container_water_1 == test_container_water_2)
    assert not (test_container_water_2 == test_container_water_1)
    # Reset max volume for future tests
    test_container_water_1.max_volume = test_container_water_2.max_volume

    # NOTE: Infinite amounts for both containers was tested with the empty
    #       container equality check.


    # ==========================================================================
    # False Case: First and second arguments have different current volumes
    # ==========================================================================
    test_container_water_1.volume = 20
    assert not (test_container_water_1 == test_container_water_2)
    # Reset current volume to match again for future tests
    test_container_water_1.volume = test_container_water_2.volume


    # ==========================================================================
    # False Case: First and second arguments have different contents
    # ==========================================================================
    
    # Test for conditions where the contents have different amounts of entries.
    # Both directions are tested.
    test_container_water_1.contents.pop(water)
    assert not (test_container_water_1 == test_container_water_2)
    assert not (test_container_water_2 == test_container_water_1)

    # Test for conditions where the contents have the same number of entries,
    # but have different substances. Both directions are tested.
    test_container_water_1.contents[dmso] = test_container_water_2.contents[water]
    assert not (test_container_water_1 == test_container_water_2)
    assert not (test_container_water_2 == test_container_water_1)
    # Reset contents to match again for future tests (need to use deepcopy
    # to avoid linking the containers' contents to the same object)
    test_container_water_1.contents = deepcopy(test_container_water_2.contents)

    # Test for conditions where the contents have the same number of entries,
    # but have different substances. Both directions are tested.
    test_container_water_1.contents[water] += 1
    assert not (test_container_water_1 == test_container_water_2)
    assert not (test_container_water_2 == test_container_water_1)
    # Reset contents to match again for future tests (need to use deepcopy
    # to avoid linking the containers' contents to the same object)
    test_container_water_1.contents = deepcopy(test_container_water_2.contents)

def test_Container___hash__(empty_container, water_stock, 
                            salt_stock, salt_water):
    """
    Unit Test for `Container.__hash__()`
    
    This unit test ensures that identical containers result in the same hashing.
    Specifically it tests the following scenarios:
    - Comparison of two calls to __hash__() by the same Container object.
    - Comparison of the hash results of two identical Container objects.
    """

    containers = [empty_container, water_stock, salt_stock, salt_water]

    # ==========================================================================
    # Equal Case: Two hashes of the same container
    # ==========================================================================

    for container in containers:
        assert container.__hash__() == container.__hash__()

    # ==========================================================================
    # Equal Case: Hashes of identical containers
    # ==========================================================================

    for container in containers:
        # Recreate the max volume parameter from the maximum volume of the 
        # current container.
        max_volume_str = f"{container.max_volume} {config.volume_storage_unit}" 
        
        # Recreate the initial_contents parameter from the contents of the
        # current container.
        identical_contents = []
        for substance, val in container.contents.items():
            qty = f"{val} {config.moles_storage_unit}"
            identical_contents.append((substance, qty))
        
        # For a given container, checks both a) an identical substance created 
        # manually with the same arguments and b) a deepcopy of the substance
        identical_container = Container(name=container.name,
                                        max_volume=max_volume_str,
                                        initial_contents=identical_contents)
        identical_container_2 = deepcopy(container)

        assert container.__hash__() == identical_container.__hash__()
        assert container.__hash__() == identical_container_2.__hash__()

def test_Container__self_add(water, dmso, salt, sodium_sulfate):
    """
    Unit Test for the function `Container._self_add()`.

    This unit test checks the following scenarios:
    - Arguments raise a `TypeError` if they are not the correct types.
    - 'quantity' argument raises a `ValueError` if it is not positive or zero.
    - 'quantity' argument raises a `ValueError` if adding it to the container
      would exceed the volume of the container.
    - Adding zero of a substance does not add it to the 
    - The substance is correctly added to the container in the following cases:
      1. Substance is added to an empty container
      2. Substance is added to a non-empty container that did not already 
         contain the substance.
      3. Substance is added to a non-empty container that did already contain
         some amount of the substance and no other substance.
      4. Substance is added to a non-empty container that did already contain
         some amount of the substance as well as other substances.
           
      The tests above check that the substance is in the container, that the amount
      of the substance in the container matches the amount specified to be added,
      that any other pre-existing substances also have the correct amounts,
      and that the overall volume of the container matches the total amount
      of substances that have been added.

    - Edge case: zero quantity addition of a substance does not add the substance
      to the container's contents if it is not already present, and does not
      change the amount of the substance if it is already present. 
    """
    # Create a new container for use in argument type/value checking
    container = Container('container', max_volume='5 mL')


    # ==========================================================================
    # Failure Case: Invalid argument types
    # ==========================================================================
    
    with pytest.raises(TypeError, match='Source must be a Substance\\.'):
        container._self_add('water', '5 mL')
    with pytest.raises(TypeError, match='Quantity must be a str\\.'):
        container._self_add(water, 5)


    # ==========================================================================
    # Failure Case: Invalid argument value - non-sensical amount to be added
    # ==========================================================================
    
    # Sub-Case: Negative additional volume
    for test_volume in test_negative_volumes:
        # Wildcard (.*) used in the regular expression because negative infinite
        # quantities are included in the test_negative_volumes list, which should 
        # trigger the 'non-finite' error instead of the 'negative error.'
        with pytest.raises(ValueError,
                    match="Cannot add a .* amount of a substance\\."):
            container._self_add(water, test_volume)

    # Sub-Case: Non finite transfer volume
    with pytest.raises(ValueError,
                match="Cannot add a non-finite amount of a substance\\."):
        container._self_add(water, 'inf L')


    # ==========================================================================
    # Failure Case: Invalid argument value - quantity exceeds container volume
    # ==========================================================================
    
    # Try to add more substance than the container can hold
    with pytest.raises(ValueError, match='Exceeded the maximum volume'):
        container._self_add(water, '10 mL')
    with pytest.raises(ValueError, match='Exceeded the maximum volume'):
        container._self_add(dmso, '20 mL')
    with pytest.raises(ValueError, match='Exceeded the maximum volume'):
        container._self_add(salt, '5.01 mL')
    with pytest.raises(ValueError, match='Exceeded the maximum volume'):
        container._self_add(sodium_sulfate, '400000 mL')

    substance_list = [water, dmso, salt, sodium_sulfate]

    # ==========================================================================
    # Success Case: Substance added to empty container
    # ==========================================================================
    #
    for substance in substance_list:
        # Create a new empty container
        container = Container('container', max_volume='5 mL')

        # Use the _self_add method to add the substance to the container
        container._self_add(substance, '5 mL')

        # Check if the substance was correctly added to the container
        assert substance in container.contents
        assert pytest.approx(container.contents[substance]) == \
                substance.convert_quantity('5 mL', config.moles_storage_unit)
        assert pytest.approx(container.volume) == Unit.convert_to_storage(5, 'mL')


    # ==========================================================================
    # Success Case: Substance added to non-empty container 
    #               (substance to-be-added is not in the container)
    # ==========================================================================
    #
    for old_substance in substance_list:
        for new_substance in substance_list:
            if new_substance is old_substance: 
                continue
            
            # Create a new empty container with the old substance in the initial
            # contents
            container = Container('container', max_volume='20 mL', 
                                initial_contents=[(old_substance, '10 mL')])

            # Use the _self_add method to add the new substance to the container
            container._self_add(new_substance, '5 mL')

            # Check if the new substance was correctly added to the container
            assert new_substance in container.contents
            assert pytest.approx(container.contents[new_substance]) == \
                    new_substance.convert_quantity('5 mL', config.moles_storage_unit)
            
            # Check that the old contents of the container are still present
            assert old_substance in container.contents
            assert pytest.approx(container.contents[old_substance]) == \
                    old_substance.convert_quantity('10 mL', config.moles_storage_unit)

            # Check that the overall volume of the container is correct
            assert pytest.approx(container.volume) == \
                Unit.convert_to_storage(15, 'mL')
            

    # ==========================================================================
    # Success Case: Substance added to non-empty container (substance to-be-
    #               added is already in the container; no other substances are
    #               present)
    # ==========================================================================
    #
    for substance in substance_list:
        # Create a new container with an initial amount of the substance
        container = Container('container', max_volume='20 mL', 
                            initial_contents=[(substance, '10 mL')])

        # Use the _self_add method to add the substance to the container
        container._self_add(substance, '5 mL')

        # Check if the substance was correctly added to the container
        assert substance in container.contents
        assert pytest.approx(container.contents[substance]) == \
                substance.convert_quantity('15 mL', config.moles_storage_unit)

        # Check that the overall volume of the container is correct
        assert pytest.approx(container.volume) == \
            Unit.convert_to_storage(15, 'mL')


    # ==========================================================================
    # Success Case: Substance added to non-empty container (substance to-be-
    #               added is already in the container and other substances are
    #               also present)
    # ==========================================================================
    #
    for old_substance in substance_list:
        for new_substance in substance_list:
            if new_substance is old_substance: 
                continue

            # Create a new container with both the old and new substance present
            container = Container('container', max_volume='30 mL', 
                                initial_contents=[(old_substance, '10 mL'),
                                                  (new_substance, '7.5 mL')])

            # Use the _self_add method to add the new substance to the container
            container._self_add(new_substance, '5 mL')

            # Check if the new substance was correctly added to the container
            assert new_substance in container.contents
            assert pytest.approx(container.contents[new_substance]) == \
                new_substance.convert_quantity('12.5 mL', config.moles_storage_unit)
            
            # Check that the old contents of the container are still present
            assert old_substance in container.contents
            assert pytest.approx(container.contents[old_substance]) == \
                    old_substance.convert_quantity('10 mL', config.moles_storage_unit)

            # Check that the overall volume of the container is correct
            assert pytest.approx(container.volume) == \
                Unit.convert_to_storage(22.5, 'mL')
            
    # ==========================================================================
    # Success Case: Zero quantity of substance added to empty/non-empty 
    #               container
    # ==========================================================================
    #
    for substance in substance_list:
        for unit in test_units:
            # Create a new empty container
            container = Container('container')

            # Use the _self_add method to add the substance to the container
            container._self_add(substance, f'0 {unit}')

            # Ensure that the substance was correctly left out of the container
            assert new_substance not in container.contents
            assert container.volume == 0
            
            # Create a new non-empty container, containing the substance
            container = Container('container', 
                                initial_contents=[(substance, '5 mL')])

            # Use the _self_add method to add the new substance to the container
            container._self_add(substance, f"0 {unit}")

            # Ensure that the substance amount is unchanged as a result of the 
            # zero-quantity addition
            assert Unit.convert_from_storage(container.volume, 'mL') == 5
        
def test_Container__set_initial_contents(water, dmso, salt):
    """
    Unit test for `Container._set_initial_contents()`

    This unit test checks the following failure scenarios:
    - Invalid argument type results in raising a `TypeError`
      - Case: Overall argument type is incorrect (not an iterable).
        - E.g. initial_contents=12
        - Note: Strings are also considered a failure case here even though they
          are an Iterable.
      - Case: An element of the of the initial contents does not match the
              format (Substance, str).
        - Sub-Case: The element is not an iterable with a length of 2.
          - E.g. inital_contents=[(12)]
          - Note: An element that is string of length 2 is also considered a 
            failure case here even though they satisfy the other conditions.
        - Sub-Case: The first entry of the element is not a substance.
        - Sub-Case: The second entry of the element is not a string.

    This unit test checks the following success scenarios:
    - Single/multiple substances with an outer iteration layer
      - E.g. initial_contents=[(water, '1 mL')]
    - Single substances WITHOUT an outer iteration layer
      - E.g. initial_contents=(water, '1 mL')
    - Repeated substances
      - E.g. initial_content=[(water, '1 mL'), (water, '1 mL')]
    - Zero quantity of substance 
    """
    
    # ==========================================================================
    # Failure Case: Invalid argument type - overall argument type is incorrect
    # ==========================================================================

    with pytest.raises(TypeError, match="Initial contents must be iterable"):
        Container('container', '1 L', 1)
    with pytest.raises(TypeError, match="Initial contents cannot be a str\\."):
        Container('container', '1 L', "inital_contents")


    # ==========================================================================
    # Failure Case: Invalid argument type - incorrect type for one or more
    #               individual entries of initial_contents argument
    # ==========================================================================

    base_error_msg = r"Invalid entry in initial_contents '.*'\. "

    # Sub-Case: Entry is not formatted as (Substance, str).
    with pytest.raises(TypeError, match=base_error_msg +
                                r"Elements must be \(Substance, str\) tuples\."):
        Container('container', '1 L', [1])
    
    # Sub-Case: First element of the entry is not a Substance
    with pytest.raises(TypeError, match=base_error_msg + 
                                  r".* is not a Substance."):
        Container('container', '1 L', [None, "1 mL"])
    with pytest.raises(TypeError, match=base_error_msg + 
                                  r".* is not a Substance."):
        Container('container', '1 L', [1, "1 mL"])

    # Sub-Case: Second element of the entry is not a str
    with pytest.raises(TypeError, match=base_error_msg + 
                                  r".* is not a str."):
        Container('container', '1 L', [water, salt])
    with pytest.raises(TypeError, match=base_error_msg + 
                                  r".* is not a str."):
        Container('container', '1 L', [(water, 1), (salt, 1)])
    with pytest.raises(TypeError, match=base_error_msg + 
                                  r".* is not a str."):
        Container('container', '1 L', [(water, None), (salt, True)])


    # ==========================================================================
    # Failure Case: Invalid argument value - invalid quantity for a substance
    # ==========================================================================

    # Sub-Case: Non-parseable quantities
    for ex in test_non_parseable_quantities:
        with pytest.raises(ValueError, match=r"Could not add '.*' of .*\."):
            container = Container('container')
            container._set_initial_contents((salt, ex))

    # Sub-Case: Invalid quantity value 
    for ex in ['-1 mol', 'inf g', 'nan L']:
        with pytest.raises(ValueError, match=r"Could not add '.*' of .*\."):
            container = Container('container')
            container._set_initial_contents((salt, ex))

    # Sub-Case: Exceeds volume of container
    with pytest.raises(ValueError, match=r"Could not add '.*' of .*\."):
            container = Container('container', '10 L')
            container._set_initial_contents((salt, '20 L'))

    

    # Test variations for initial contents
    test_initial_contents = [[(water, '1 mol')],
                             [(water, '1 g')],
                             [(water, '1 L')],
                             [(salt, '10 g')],
                             [(salt, '10 mol')],
                             [(salt, '10 L')],
                             [(water, '1 kL')],
                             [(salt, '5 mg')],
                             [(water, '1 L'), (salt, '5 mg')],
                             [(dmso, '12 mL'), (salt, '10 g')],
                             [(water, '1 g'), (salt, '1 g'), (dmso, '1 g')],
                            ]
    
    # ==========================================================================
    # Success Case: Standard substance variations (with outer iterable layer)
    # ==========================================================================
    
    for init_contents in test_initial_contents:
        container = Container('container')
        container._set_initial_contents(init_contents)

        for substance, quantity in init_contents:
            assert substance in container.contents, \
                f"Container 'contents' is missing substance '{substance}' that " \
                "was present in 'initial_contents' constructor argument."
            
            # NOTE: This line creates an interdependence between unit tests. 
            # If Substance.convert_quantity() is not working, this test will not
            # work correctly.
            umols_substance = substance.convert_quantity(quantity, 
                                                         config.moles_storage_unit)
            assert container.contents[substance] == pytest.approx(umols_substance)
    

    # ==========================================================================
    # Success Case: Single substance in contents WITHOUT an outer iterable type
    #                  E.g. initial_contents=(water, '1 mL')
    # ==========================================================================
    
    # Test with no maximum volume & list type
    container = Container('container')
    container._set_initial_contents([water, '1 L'])
    assert water in container.contents 
    expected_water = water.convert_quantity('1 L', config.moles_storage_unit)
    assert container.contents[water] == pytest.approx(expected_water, rel=1e-12)

    # Test with maximum volume & tuple type
    container = Container('container', '10 L')
    container._set_initial_contents((dmso, '1 L'))
    assert dmso in container.contents 
    expected_dmso = dmso.convert_quantity('1 L', config.moles_storage_unit)
    assert container.contents[dmso] == pytest.approx(expected_dmso, rel=1e-12)


    # ==========================================================================
    # Success Case: Repeated entry in initial_contents
    # ==========================================================================
    
    # Single repeated substance
    container = Container('container')
    container._set_initial_contents(([water, '1 L'], [water, '1 L']))
    assert water in container.contents 
    expected_water = water.convert_quantity('2 L', config.moles_storage_unit)
    assert container.contents[water] == pytest.approx(expected_water, rel=1e-12)

    # Multiple repeated substances
    container = Container('container')
    repeated_initial_contents = []
    for i in range(5):
        repeated_initial_contents.append((water, '500 uL'))
        repeated_initial_contents.append((salt, '5 ug'))
    container._set_initial_contents(repeated_initial_contents)

    assert water in container.contents 
    expected_water = water.convert_quantity('2500 uL', config.moles_storage_unit)
    assert container.contents[water] == pytest.approx(expected_water, rel=1e-12)

    assert salt in container.contents 
    expected_salt = salt.convert_quantity('25 ug', config.moles_storage_unit)
    assert container.contents[salt] == pytest.approx(expected_salt)


    # ==========================================================================
    # Success Case: Zero quantity for substance
    # ==========================================================================
    
    # Substance should not be found in the container
    for unit in test_base_units:
        container = Container('container')
        container._set_initial_contents(([dmso, f'0 {unit}']))
        assert dmso not in container.contents 
    
def test_Container__transfer(water, dmso, salt, sodium_sulfate, 
                             empty_container, empty_plate,
                             mocker):
    """
    Unit Test for the function `Container._transfer()`
    
    This unit test checks the following failure scenarios:
    - Arguments raise a `TypeError` if they are not the correct types.
    - Negative quantities raise a `ValueError`.
    - Non-finite quantities raise a `ValueError`.
    - Transfers which require a quantity greater than the total contents of the
      source container raise a `ValueError`.
    - Transfers which would exceed the maximum volume of the destination
      container raise a `ValueError`.
    
    This unit test checks the following success scenarios:
    - All unit types (each base unit covered, as well as various prefixes)
    - Partial transfer vs. full transfer of source container contents
    - Finite volume vs. infinite volume source/destination containers
      - Subcases for finite volume: transfer fills the entire container vs. 
        transfer does not fill the entire container
    - Empty destination container vs. non-empty destination container 
      - Subcases for non-empty destination container: no overlapping substances
        with source container vs. one or more overlapping substances with source
        container.

    This unit test depends on the correctness of the following functions:
    - `Substance.convert_quantity()`

    TODO: Include checks for proper instruction generation.
    """

    # Create containers to use for type-checking and illegal argument value tests
    container1 = Container('container1', '10 mL', 
                           initial_contents=[(water, '10 mL')])
    container2 = Container('container2', '10 mL')

    # ==========================================================================
    # Failure Case: Invalid argument type(s)
    # ==========================================================================
    
    with pytest.raises(TypeError, match='Invalid source type\\.'):
        container1._transfer(1, '10 mL')
    with pytest.raises(TypeError, match='Invalid source type\\.'):
        container1._transfer(None, '10 mL')
    with pytest.raises(TypeError, match='Invalid source type\\.'):
        container1._transfer([], '10 mL')
    with pytest.raises(TypeError, match='Invalid source type\\.'):
        container1._transfer(water, '10 mL')
    with pytest.raises(TypeError, match='Invalid source type\\.'):
        container1._transfer(empty_plate, '10 mL')

    with pytest.raises(TypeError, match='Quantity must be str\\.'):
        container1._transfer(empty_container, 10)
    with pytest.raises(TypeError, match='Quantity must be str\\.'):
        container1._transfer(empty_container, None)
    with pytest.raises(TypeError, match='Quantity must be str\\.'):
        container1._transfer(empty_container, [])
    with pytest.raises(TypeError, match='Quantity must be str\\.'):
        container1._transfer(empty_container, water)
    with pytest.raises(TypeError, match='Quantity must be str\\.'):
        container1._transfer(empty_container, empty_container)
    with pytest.raises(TypeError, match='Quantity must be str\\.'):
        container1._transfer(empty_container, empty_plate)


    # ==========================================================================
    # Failure Case: Negative transfer quantity 
    # ==========================================================================
    
    for test_volume in test_negative_quantities:
        # Wildcard added because negative infinite quantities are included in
        # the negative volumes list, which will trigger the non-finite error
        # instead of the negative error.
        with pytest.raises(ValueError, 
                match='Cannot transfer a .* amount of a substance\\.'):
            container2._transfer(container1, test_volume)


    # ==========================================================================
    # Failure Case: Non-finite transfer quantity
    # ==========================================================================
    
    for unit in test_base_units:
        with pytest.raises(ValueError, 
                match='Cannot transfer a non-finite amount of a substance\\.'):
            container2._transfer(container1, 'inf ' + unit)


    # ==========================================================================
    # Failure Case: Quantity with invalid unit (mocking used for 
    #               Unit.parse_quantity() to reach the error)
    # ==========================================================================
    
    # Save a copy of the real Unit.parse_quantity so it can be reselt at the end
    # of this test.
    real_parse_quantity = Unit.parse_quantity

    # Replace the real Unit.parse_quantity() with the mock version
    mocker.patch.object(Unit, 'parse_quantity', mock_parse_quantity)

    for value in ['0.5', '10', '4', '12', '200000', '7.42']:
        for unit in ['pestles', 'C', 'units', 'quantities']:
            quantity = value + ' ' + unit
            with pytest.raises(ValueError, 
                               match=f'Invalid quantity unit \'{unit}\'\\.'):
                container2._transfer(container1, quantity)
    
    # Revert Unit.parse_quantity() to the original version
    mocker.patch.object(Unit, 'parse_quantity', real_parse_quantity)


    # ==========================================================================
    # Failure Case: transfer quantity exceeds amount in source container
    # ==========================================================================
    #
    # TODO: This test includes a fairly flexible regular expression to ensure 
    #       that the appropriate error messages are being generated, but to 
    #       properly test this failure case, the message-checking should be 
    #       much stricter.

    # Test for all variations of units
    for base_unit in test_base_units:
        for prefix in test_prefixes:
            # Create the prefixed unit from the prefix and base unit
            unit = prefix + base_unit

            # Create a container with 10 'unit' of water.
            test_container = Container('c3', initial_contents=[(water, '10 ' 
                                                                + unit)])
            # Check that a value error is raised with a message that:
            #  a) starts with the correct error phrase, and 
            #  b) contains the correct base unit
            with pytest.raises(ValueError, 
                        match='Not enough mixture in source container' + 
                                f'.*{base_unit}.*'):
                container2._transfer(test_container, '20 ' + unit)
    

    # ==========================================================================
    # Failure Case: Transfer of the specified quantity would exceed the maximum
    #               volume of the destination container
    # ==========================================================================
    #
    # TODO: Improve this failure case. It relies on the principle that, because
    #       the density of water is 1 g/mL, 1.01 * any of the base units will
    #       always be greater than 1 mL (1.01 g > 1 mL, 1.01 L > 1 mL, and 
    #       1.01 mol > 1 mL). So, the values have been sneakily chosen to test
    #       this failure case for all of the base units while not having to 
    #       adjust the container volume. This should be made more rigorous.
    test_container2 = Container('tc2', '1 mL') 
    for unit in test_base_units:
        test_container = Container('tc', 
                                   initial_contents=[(water, '1.01 ' + unit)])
        with pytest.raises(ValueError, match='Exceeded the maximum volume'):
            test_container2._transfer(test_container, '1.01 ' + unit)


    # ==========================================================================
    # Success Case: Transfer to an empty container with infinite volume
    #               (partial and full transfer tested)
    # ==========================================================================
    
    # Define a helper function for generating the assert statements (assumes
    # the container only contains one substance; used in the next success case
    # too)
    def assert_contents_helper(container : Container, sub : Substance, 
                               amount : float, unit : str):
        # Assert that the recorded moles of the substance in the container
        # matches the specified amount    
        assert pytest.approx(container.contents.get(sub, 0)) == \
            sub.convert_quantity(f"{amount} {unit}", config.moles_storage_unit)
        
        # Assert that the total volume of the container's contents matches
        # the specified amount
        assert pytest.approx(container.volume) == \
            sub.convert_quantity(f"{amount} {unit}", config.volume_storage_unit)

    # Test all unit variations
    for unit in test_units:
        # Construct the two containers
        container1 = Container('container1', 
                               initial_contents=[(water, f"5 {unit}")])
        container2 = Container('container2')
        
        # Partial Transfer
        # ------------------
        #
        # Use _transfer() to transfer some (but not all) of the first 
        # container's contents to the second container.
        c1_prime, c2_prime = container2._transfer(container1, f"2 {unit}")

        # Ensure that the original source container is unchanged
        assert_contents_helper(container1, water, 5, unit)

        # Ensure that the original destination container is unchanged
        assert water not in container2.contents
        assert_contents_helper(container2, water, 0, unit)

        # Ensure that the substance was correctly transferred to the new object 
        # representing the post-transfer second container 
        assert water in c2_prime.contents
        assert_contents_helper(c2_prime, water, 2, unit)

        # Ensure that the substance was correctly transferred from the new 
        # object representing the post-transfer first container
        assert_contents_helper(c1_prime, water, 3, unit)

        # Full Transfer
        # ------------------
        #
        # Use _transfer() to transfer all of the first container's contents to
        # the second container.
        c1_prime, c2_prime = container2._transfer(container1, f"5 {unit}")

        # Ensure that the original source container is unchanged
        assert_contents_helper(container1, water, 5, unit)

        # Ensure that the original destination container is unchanged
        assert water not in container2.contents
        assert_contents_helper(container2, water, 0, unit)

        # Ensure that the substance was correctly transferred to the new object 
        # representing the post-transfer second container 
        assert water in c2_prime.contents
        assert_contents_helper(c2_prime, water, 5, unit)

        # Ensure that the substance was correctly transferred from the new 
        # object representing the post-transfer first container
        assert water not in c1_prime.contents
        assert_contents_helper(c1_prime, water, 0, unit)



    # ========================================================================
    # Success Case: Transfer to an empty container with finite volume
    #               (partial and full transfer tested)
    # ========================================================================

    # Test all unit variations
    for idx, unit in enumerate(test_units):
        # Construct the source container with a quantity of water as its
        # starting contents
        container1 = Container('container1', 
                            initial_contents=[(water, f"5 {unit}")])
            
        # Use the "evenness" of the loop index to create two different cases
        # within the base units as a way to test different variations for 
        # max volume:
        #   1. If odd, create the container such that the maximum volume is
        #      exactly the transfer quantity
        #   2. If even, create the container such that the maximum volume is
        #      twice the transfer quantity
        #
        # NOTE: This creates a dependency on Substance.convert_quantity(). Ideally, this 
        # unit test interdependency should be removed, but because the mock 
        # function would essentially need to be a copy of the real function, 
        # mocking it did not seem like the right decision.
        if (idx) % 2:
            max_vol = water.convert_quantity(f"5 {unit}", 'L')
        else:
            max_vol = water.convert_quantity(f"10 {unit}", 'L')
        max_vol = f"{max_vol} L"

        # Construct the destination container, ensuring the volume is set
        # high enough to contain the contents of the first container.
        container2 = Container('container2', max_volume=max_vol)
        
        # Partial Transfer
        # ------------------
        #
        # Use _transfer() to transfer some (but not all) of the first 
        # container's contents to the second container.
        c1_prime, c2_prime = container2._transfer(container1, f"2 {unit}")

        # Ensure that the original source container is unchanged
        assert_contents_helper(container1, water, 5, unit)

        # Ensure that the original destination container is unchanged
        assert water not in container2.contents
        assert_contents_helper(container2, water, 0, unit)

        # Ensure that the substance was correctly transferred to the new 
        # object representing the post-transfer second container 
        assert water in c2_prime.contents
        assert_contents_helper(c2_prime, water, 2, unit)

        # Ensure that the substance was correctly transferred from the new 
        # object representing the post-transfer first container
        assert_contents_helper(c1_prime, water, 3, unit)

        # Full Transfer
        # ------------------
        #
        # Use _transfer() to transfer all of the first container's contents to
        # the second container.
        c1_prime, c2_prime = container2._transfer(container1, f"5 {unit}")

        # Ensure that the original source container is unchanged
        assert_contents_helper(container1, water, 5, unit)

        # Ensure that the original destination container is unchanged
        assert water not in container2.contents
        assert_contents_helper(container2, water, 0, unit)

        # Ensure that the substance was correctly transferred to the new object 
        # representing the post-transfer second container 
        assert water in c2_prime.contents
        assert_contents_helper(c2_prime, water, 5, unit)

        # Ensure that the substance was correctly transferred from the new 
        # object representing the post-transfer first container
        assert water not in c1_prime.contents
        assert_contents_helper(c1_prime, water, 0, unit)



    # ==========================================================================
    # Success Case: Transfer to an non-empty container with non-overlapping
    #               substances (partial and full transfer tested)
    # ==========================================================================

    # Define a helper function for generating the assert statements for
    # the container's contents (this has been modified to remove the 'total
    # volume' assertion that was present in the helper function used in the 
    # tests of the last two success cases).
    def assert_contents_helper(container : Container, sub : Substance, 
                               amount : float, unit : str, msg : str = ""):
        
        if amount > 0:
            # Assert that the substance is in the container's contents 
            assert sub in container.contents, msg
        else:
            # Assert that the substance is NOT in the container's contents
            assert sub not in container.contents, msg
        
        # Assert that the recorded moles of the substance in the container
        # matches the specified amount  
        amount = round(sub.convert_quantity(f"{amount} {unit}", 
                                    config.moles_storage_unit), 
                                    config.internal_precision)
        
        # TODO: Remove the 'rel' parameter and fix precision issue
        assert pytest.approx(container.contents.get(sub, 0), rel=0.001) == \
            amount, msg

    # Test all unit variations
    for idx, unit in enumerate(test_units):
        # Construct the source container with a quantity of water and salt as 
        # its starting contents
        container1 = Container('container1', 
                            initial_contents=[(water, f"5 {unit}"), 
                                              (salt, f"5 {unit}")])
            
        # Construct the non-empty destination container with non-overlapping 
        # substances (dmso and sodium sulfate).
        container2 = Container('container2', 
                            initial_contents=[(dmso, f"20 {unit}"), 
                                              (sodium_sulfate, f"1 {unit}")])
        
        # Partial Transfer
        # ------------------
        #
        # Use _transfer() to transfer some (but not all) of the first 
        # container's contents to the second container.
        c1_prime, c2_prime = container2._transfer(container1, f"2 {unit}")

        # Ensure that the original source container is unchanged
        assert_msg = "Transfer incorrectly mutated the input source " + \
                     "container object!"
        assert_contents_helper(container1, water, 5, unit, assert_msg)
        assert_contents_helper(container1, salt, 5, unit, assert_msg)

        # Ensure that the original destination container is unchanged
        assert_msg = "Transfer incorrectly mutated the input destination " + \
                     "container object!"
        assert_contents_helper(container2, dmso, 20, unit, assert_msg)
        assert_contents_helper(container2, sodium_sulfate, 1, unit, assert_msg)
        assert water not in container2.contents, assert_msg
        assert salt not in container2.contents, assert_msg

        # Ensure that the contents of the source container were correctly
        # transferred to the new object representing the post-transfer 
        # second container
        assert_msg = "New post-transfer destination container contents do " + \
                     "not contain the correct amounts of the substances " + \
                     "transferred from the source container!"
        assert_contents_helper(c2_prime, water, 1, unit, assert_msg)
        assert_contents_helper(c2_prime, salt, 1, unit, assert_msg)

        # Ensure that the original contents of the destination container were 
        # maintained in the new object representing the post-transfer
        # second container 
        assert_msg = "New post-transfer destination container contents did " + \
                     "not maintain the correct amounts for its pre-existing" + \
                     " contents!"
        assert_contents_helper(c2_prime, dmso, 20, unit, assert_msg)
        assert_contents_helper(c2_prime, sodium_sulfate, 1, unit, assert_msg)

        # Ensure that the substance was correctly transferred from the new 
        # object representing the post-transfer first container
        assert_msg = "New post-transfer source container contents do not " + \
                     "contain the correct amounts of the substances left " + \
                     "over from the transfer!"
        assert_contents_helper(c1_prime, water, 4, unit, assert_msg)
        assert_contents_helper(c1_prime, salt, 4, unit, assert_msg)

        # Full Transfer
        # ------------------
        #
        # Use _transfer() to transfer all of the first container's contents to
        # the second container.
        c1_prime, c2_prime = container2._transfer(container1, f"10 {unit}")

        # Ensure that the original source container is unchanged
        assert_msg = "Transfer incorrectly mutated the input source " + \
                     "container object!"
        assert_contents_helper(container1, water, 5, unit, assert_msg)
        assert_contents_helper(container1, salt, 5, unit, assert_msg)

        # Ensure that the original destination container is unchanged
        assert_msg = "Transfer incorrectly mutated the input destination " + \
                     "container object!"
        assert_contents_helper(container2, dmso, 20, unit, assert_msg)
        assert_contents_helper(container2, sodium_sulfate, 1, unit, assert_msg)
        assert water not in container2.contents
        assert salt not in container2.contents

        # Ensure that the contents of the source container were correctly
        # transferred to the new object representing the post-transfer 
        # second container
        assert_msg = "New post-transfer destination container contents do " + \
                     "not contain the correct amounts of the substances " + \
                     "transferred from the source container!"
        assert_contents_helper(c2_prime, water, 5, unit, assert_msg)
        assert_contents_helper(c2_prime, salt, 5, unit, assert_msg)

        # Ensure that the original contents of the destination container were 
        # maintained in the new object representing the post-transfer
        # second container 
        assert_msg = "New post-transfer destination container contents did " + \
                     "not maintain the correct amounts for its pre-existing" + \
                     " contents!"
        assert_contents_helper(c2_prime, dmso, 20, unit, assert_msg)
        assert_contents_helper(c2_prime, sodium_sulfate, 1, unit, assert_msg)

        # Ensure that the substance was correctly transferred from the new 
        # object representing the post-transfer first container
        assert_msg = "New post-transfer source container contents were not " + \
                     "entirely removed after a full transfer of the source " + \
                     "container's contents!"
        assert_contents_helper(c1_prime, water, 0, unit)
        assert_contents_helper(c1_prime, salt, 0, unit)
        assert c1_prime.volume == 0, assert_msg


    # ==========================================================================
    # Success Case: Transfer to an non-empty container with overlapping
    #               substances (partial and full transfer tested)
    # ==========================================================================

    # Test all unit variations
    for idx, unit in enumerate(test_units):
        # Construct the source container with a quantity of water and salt as 
        # its starting contents
        container1 = Container('container1', 
                            initial_contents=[(water, f"5 {unit}"), 
                                              (salt, f"5 {unit}")])
            
        # Construct the non-empty destination container with overlapping 
        # substances (water and salt).
        container2 = Container('container2', 
                            initial_contents=[(water, f"20 {unit}"), 
                                              (salt, f"1 {unit}")])
        
        # Partial Transfer
        # ------------------
        #
        # Use _transfer() to transfer some (but not all) of the first 
        # container's contents to the second container.
        c1_prime, c2_prime = container2._transfer(container1, f"2 {unit}")

        # Ensure that the original source container is unchanged
        assert_msg = "Transfer incorrectly mutated the input source " + \
                     "container object!"
        assert_contents_helper(container1, water, 5, unit, assert_msg)
        assert_contents_helper(container1, salt, 5, unit, assert_msg)

        # Ensure that the original destination container is unchanged
        assert_msg = "Transfer incorrectly mutated the input destination " + \
                     "container object!"
        assert_contents_helper(container2, water, 20, unit, assert_msg)
        assert_contents_helper(container2, salt, 1, unit, assert_msg)

        # Ensure that the contents of the source container were correctly
        # transferred to the new object representing the post-transfer 
        # second container
        assert_msg = "New post-transfer destination container contents do " + \
                     "not contain the correct amounts of the substances " + \
                     "transferred from the source container!"
        assert_contents_helper(c2_prime, water, 21, unit, assert_msg)
        assert_contents_helper(c2_prime, salt, 2, unit, assert_msg)

        # Ensure that the substance was correctly transferred from the new 
        # object representing the post-transfer first container
        assert_msg = "New post-transfer source container contents do not " + \
                     "contain the correct amounts of the substances left " + \
                     "over from the transfer!"
        assert_contents_helper(c1_prime, water, 4, unit, assert_msg)
        assert_contents_helper(c1_prime, salt, 4, unit, assert_msg)

        # Full Transfer
        # ------------------
        #
        # Use _transfer() to transfer all of the first container's contents to
        # the second container.
        c1_prime, c2_prime = container2._transfer(container1, f"10 {unit}")

        # Ensure that the original source container is unchanged
        assert_msg = "Transfer incorrectly mutated the input source " + \
                     "container object!"
        assert_contents_helper(container1, water, 5, unit, assert_msg)
        assert_contents_helper(container1, salt, 5, unit, assert_msg)

        # Ensure that the original destination container is unchanged
        assert_msg = "Transfer incorrectly mutated the input destination " + \
                     "container object!"
        assert_contents_helper(container2, water, 20, unit, assert_msg)
        assert_contents_helper(container2, salt, 1, unit, assert_msg)

        # Ensure that the contents of the source container were correctly
        # transferred to the new object representing the post-transfer 
        # second container
        assert_msg = "New post-transfer destination container contents do " + \
                     "not contain the correct amounts of the substances " + \
                     "transferred from the source container!"
        assert_contents_helper(c2_prime, water, 25, unit, assert_msg)
        assert_contents_helper(c2_prime, salt, 6, unit, assert_msg)

        # Ensure that the substance was correctly transferred from the new 
        # object representing the post-transfer first container
        assert_msg = "New post-transfer source container contents were not " + \
                     "entirely removed after a full transfer of the source " + \
                     "container's contents!"
        assert_contents_helper(c1_prime, water, 0, unit)
        assert_contents_helper(c1_prime, salt, 0, unit)
        assert c1_prime.volume == 0, assert_msg

def test_Container__transfer_slice(empty_container, empty_plate, water_plate,
                                   water, mocker):
    """
    Unit Test for `Container._transfer_slice()`

    This unit test checks for the following failure scenarios:
    - Invalid argument type for source_slice results in raising a `TypeError`
    - TypeErrors produced by the subcall to _transfer result in a `TypeError` 
    - ValueErrors produced by the subcall to _tranfer result in a `ValueError`
    - Transfer volume exceeds the volume of the source plate well
    - Transfer results in overflowing the destination container

    This unit test checks for the following success scenarios:
    - Partial transfer of every well in plate to container
    - Full transfer of every well plate contents to container
    - Partial transfer of slice of wells in plate to container
    """

    # ==========================================================================
    # Failure Case: Invalid source type
    # ==========================================================================
    
    for non_plate in [None, False, 1, '1', (1,), [], {}, empty_container]:
        with pytest.raises(TypeError, match="Invalid source type."):
            empty_container._transfer_slice(non_plate, '1 mL')


    # ==========================================================================
    # Failure Case: TypeError from subcall to Container._transfer()
    # ==========================================================================
    
    # Store the true function in a variable so that it can be called later
    real__transfer = Container._transfer

    # Set up mock function for Container._transfer()
    _type_error_message = "THIS IS A TEST TYPE ERROR!"
    def mock__transfer(container, source, quantity):
        raise TypeError(_type_error_message)

    # Replace calls to Container._transfer and Container._transfer_slice functions
    # with calls to the mock versions
    mocker.patch.object(Container, '_transfer', mock__transfer)
    
    # Check that this function correctly raises any type errors for the keywords
    # generated by the sub-call to Container._compute_solution_contents()
    with pytest.raises(TypeError, match=_type_error_message):
        empty_container._transfer_slice(water_plate, '10 uL')

    # Revert Container._transfer() to its original form
    mocker.patch.object(Container, '_transfer', real__transfer)


    # ==========================================================================
    # Failure Case: ValueError from subcall to Container._transfer()
    # ==========================================================================
    
    # Store the true function in a variable so that it can be called later
    real__transfer = Container._transfer

    # Set up mock function for Container._transfer()
    _value_error_message = "THIS IS A TEST VALUE ERROR!"
    def mock__transfer(container, source, quantity):
        raise TypeError(_value_error_message)

    # Replace calls to Container._transfer and Container._transfer_slice functions
    # with calls to the mock versions
    mocker.patch.object(Container, '_transfer', mock__transfer)
    
    # Check that this function correctly raises any type errors for the keywords
    # generated by the sub-call to Container._compute_solution_contents()
    with pytest.raises(TypeError, match=_value_error_message):
        empty_container._transfer_slice(water_plate, '10 uL')

    # Revert Container._transfer() to its original form
    mocker.patch.object(Container, '_transfer', real__transfer)


    # ==========================================================================
    # Failure Case: Transfer exceeds the plate well volume
    # ==========================================================================
    
    with pytest.raises(ValueError):
        empty_container._transfer_slice(water_plate, '1 L')
    
    
    # ==========================================================================
    # Failure Case: Transfer overflows the destination container
    # ==========================================================================
    
    # Create a container with a maximum volume of 500 uL
    container = Container('container', '80 uL')


    # Sub-Case: Overflow on first transfer
    # -------------------------------------

    # Attempt to transfer 200 uL from each well to the container.
    with pytest.raises(ValueError):
        container._transfer_slice(water_plate, '100 uL')


    # Sub-Case: Overflow on midway transfer
    # --------------------------------------

    # Attempt to transfer 10 uL from each well to the container (this will 
    # exceed the maximum volume of the container, as there are 96 wells in the
    # plate, resulting in a total attempted transfer volume of 960 uL).
    with pytest.raises(ValueError):
        container._transfer_slice(water_plate, '10 uL')

    # NOTE: This sub-case assumes that the water plate has more than 8 wells.
    #       If this is ever changed, the test will need to be adjusted so that
    #       the transfer still overflows the container.
    
    
    # ==========================================================================
    # Success Case: Partial transfer of all wells to the container
    # ==========================================================================
    
    # Transfer 10 uL from each well of the water plate to the container. 
    plate_2, water_cont = empty_container._transfer_slice(water_plate, '10 uL')

    # Calculate the total volume of water trasnferred from the water plate
    num_wells = water_plate.n_rows * water_plate.n_columns
    transfer_vol = 10 * num_wells

    # Ensure that the transfer was successful. The water plate should have
    # 960 uL less water, and the container should have 960 uL of water.
    transfer_amt = water.convert(transfer_vol, 'uL', config.moles_storage_unit)
    assert water_cont.contents[water] == pytest.approx(transfer_amt, rel=1e-12)
    assert plate_2.get_volume('uL') == water_plate.get_volume('uL') - transfer_vol


    # ==========================================================================
    # Success Case: Full transfer of all wells to the container
    # ==========================================================================
    
    # Get the amount of water in each well of the well plate
    total_vol = water_plate.get_volume('uL') 
    transfer_vol = total_vol / num_wells

    # Transfer 10 uL from each well of the water plate to the container.
    qty = str(transfer_vol) + ' uL' 
    plate_2, water_cont = empty_container._transfer_slice(water_plate, qty)

    # Ensure that the transfer was successful. The water plate should have
    # no water, and the container should have all of the water that was in the
    # water plate.
    transfer_amt = water.convert(total_vol, 'uL', config.moles_storage_unit)
    assert water_cont.contents[water] == pytest.approx(transfer_amt, rel=1e-12)
    assert plate_2.get_volume('uL') == 0
    assert len(plate_2.get_substances()) == 0


    # ==========================================================================
    # Success Case: Partial transfer of slice of wells to the container
    # ==========================================================================
    
    # Set the plate slice to the top left 2x2 wells of the water plate
    plate_slice = water_plate['A':'B',1:2]

    # Transfer 10 uL from each well of the water plate to the container. 
    plate_2, water_cont = empty_container._transfer_slice(plate_slice, '10 uL')

    # Ensure that the transfer was successful. The container should have 40 uL 
    # of water, and the top-left 2x2 wells of the water plate should each have 
    # 10 less uL of water.

    # Ensure that the water was transferred to the new container.
    transfer_amt = water.convert(40, 'uL', config.moles_storage_unit)
    assert water_cont.contents[water] == pytest.approx(transfer_amt, rel=1e-12)

    # Ensure that the total volume of the water plate has been reduced by 40 uL.
    assert plate_2.get_volume('uL') == water_plate.get_volume('uL') - 40 

    for i, j in product(range(plate_2.n_rows), range(plate_2.n_columns)):
        # Ensure that the top-left 2x2 wells of the water plate have 10 uL less 
        # water.        
        if i < 2 and j < 2:
            assert plate_2.wells[i,j].get_volume('uL') == \
                    water_plate.wells[i,j].get_volume('uL') - 10
        
        # Ensure that all other wells of the water plate have the same volume
        else:
            assert plate_2.wells[i,j].get_volume('uL') == \
                    water_plate.wells[i,j].get_volume('uL')

def test_Container_has_liquid(empty_container, water_stock, 
                              salt_stock, salt_water):
    """
    Unit Test for `Container.has_liquid()`

    This unit test checks the following scenarios:
    - Empty container (should return False)
    - Non-empty container with no liquid (should return False)
    - Non-empty container with only liquid (should return True)
    - Non-empty container with both solids and liquid (should return True)
    """

    assert not empty_container.has_liquid()
    assert not salt_stock.has_liquid()
    assert water_stock.has_liquid()
    assert salt_water.has_liquid()  

def test_Container_get_substances(empty_container, water, salt, sodium_sulfate,
                                  water_stock, salt_water):
    """
    Unit Test for `Container.get_substances()`

    This unit test checks the following success scenarios:
    - Empty container
    - Non-empty container with one substance
    - Non-empty container with multiple substances
    """

    # ==========================================================================
    # Success Case: Empty container
    # ==========================================================================
    
    substances = empty_container.get_substances()

    assert len(substances) == 0
    assert salt not in substances
    assert water not in substances
    assert sodium_sulfate not in substances


    # ==========================================================================
    # Success Case: Non-empty container with one substance
    # ==========================================================================

    substances = water_stock.get_substances()

    assert len(substances) == 1
    assert water in substances
    assert salt not in substances
    assert sodium_sulfate not in substances


    # ==========================================================================
    # Success Case: Non-empty container with one substance
    # ==========================================================================

    substances = salt_water.get_substances()

    assert len(substances) == 2
    assert water in substances
    assert salt in substances
    assert sodium_sulfate not in substances

def test_Container_get_mass(empty_container, water, salt, sodium_sulfate, 
                            water_stock):
    """
    Unit Test for `Container.get_mass()`

    This unit test checks the following failure scenarios:
    - Invalid argument types result in raising a `TypeError`
    - Invalid value for 'unit' results in raising a `ValueError`

    This unit test checks for the following success scenarios:
    - Valid unit provided for empty container (with/without substance argument)
    - Valid unit provided for non-empty container (with/without substance argument)
    """

    # ==========================================================================
    # Failure Case: Invalid argument types
    # ==========================================================================
    
    with pytest.raises(TypeError, match="Unit must be a str\\."):
        empty_container.get_mass(123)
    with pytest.raises(TypeError, match="Unit must be a str\\."):
        empty_container.get_mass(None)

    with pytest.raises(TypeError, match="Substance argument must be a Substance or None\\."):
        empty_container.get_mass('g', 123)
    with pytest.raises(TypeError, match="Substance argument must be a Substance or None\\."):
        empty_container.get_mass('g', "invalid")

    # ==========================================================================
    # Failure Case: Invalid value for 'unit'
    # ==========================================================================
    
    # Sub-Case: Non-mass unit (e.g. 'L' or 'mol' or any invalid unit)
    with pytest.raises(ValueError, match="Invalid mass unit "):
        empty_container.get_mass('L')
    with pytest.raises(ValueError, match="Invalid mass unit "):
        empty_container.get_mass('mol')
    with pytest.raises(ValueError, match="Invalid mass unit "):
        empty_container.get_mass('2 mL')
    for unit in test_invalid_units:
        with pytest.raises(ValueError, match="Invalid mass unit "):
            empty_container.get_mass(unit)

    # Sub-Case: Invalid unit values (satisfy 'g' end check)
    with pytest.raises(ValueError):
        empty_container.get_mass('jg')
    with pytest.raises(ValueError):
        empty_container.get_mass('weg')
    with pytest.raises(ValueError):
        empty_container.get_mass('10 kg')

    
    # ==========================================================================
    # Success Case: Empty container
    # ==========================================================================
    
    for prefix in test_prefixes:
        for substance in [None, water, salt, sodium_sulfate]:
            mass = empty_container.get_mass(prefix + 'g', substance)
            assert mass == 0


    # ==========================================================================
    # Success Case: Non-empty container
    # ==========================================================================
    
    for prefix, mult in zip(test_prefixes, test_prefix_multipliers):
        # Fixture is created with 1000 mL of water (which is 1000 g because of 
        # water's density of 1 g/mL). Thus, both total mass and water mass 
        # should be 1000 g. The assert statement scales this amount by the
        # multiplier for the current prefix.
        for substance in [None, water]:
            mass = water_stock.get_mass(prefix + 'g', substance)
            assert mass == pytest.approx(1000 / mult, rel=1e-10)

        # These substances are not in the water stock, so their masses should be
        # zero.
        for substance in [salt, sodium_sulfate]:
            mass = water_stock.get_mass(prefix + 'g', substance)
            assert mass == 0

def test_Container_get_moles(empty_container, water, salt, sodium_sulfate, 
                             water_stock):
    """
    Unit Test for `Container.get_moles()`

    This unit test checks the following failure scenarios:
    - Invalid argument types result in raising a `TypeError`
    - Invalid value for 'unit' results in raising a `ValueError`

    This unit test checks for the following success scenarios:
    - Valid unit provided for empty container (with/without substance argument)
    - Valid unit provided for non-empty container (with/without substance argument)
    """

    # ==========================================================================
    # Failure Case: Invalid argument types
    # ==========================================================================
    
    with pytest.raises(TypeError, match="Unit must be a str\\."):
        empty_container.get_moles(None)
    with pytest.raises(TypeError, match="Unit must be a str\\."):
        empty_container.get_moles(456)

    with pytest.raises(TypeError, match="Substance argument must be a Substance or None\\."):
        empty_container.get_moles('mol', 456)
    with pytest.raises(TypeError, match="Substance argument must be a Substance or None\\."):
        empty_container.get_moles('mol', "invalid")

    # ==========================================================================
    # Failure Case: Invalid value for 'unit'
    # ==========================================================================
    
    # Sub-Case: Non-mole unit (e.g. 'g' or 'L' or any invalid unit)
    with pytest.raises(ValueError, match="Invalid mole unit "):
        empty_container.get_moles('g')
    with pytest.raises(ValueError, match="Invalid mole unit "):
        empty_container.get_moles('L')
    with pytest.raises(ValueError, match="Invalid mole unit "):
        empty_container.get_moles('2 g')
    for unit in test_invalid_units:
        with pytest.raises(ValueError, match="Invalid mole unit "):
            empty_container.get_moles(unit)

    # Sub-Case: Invalid unit values (satisfy 'mol' end check)
    with pytest.raises(ValueError):
        empty_container.get_moles('jmol')
    with pytest.raises(ValueError):
        empty_container.get_moles('wegmol')
    with pytest.raises(ValueError):
        empty_container.get_moles('10 mol')

    
    # ==========================================================================
    # Success Case: Empty container
    # ==========================================================================
    
    for prefix in test_prefixes:
        for substance in [None, water, salt, sodium_sulfate]:
            moles = empty_container.get_moles(prefix + 'mol', substance)
            assert moles == 0


    # ==========================================================================
    # Success Case: Non-empty container
    # ==========================================================================
    
    for prefix, mult in zip(test_prefixes, test_prefix_multipliers):
        # Fixture is created with 1000 mL of water (which is 1000 g because of 
        # water's density of 1 g/mL). Thus, both total moles and water moles 
        # should be 1000 g / 18.0153 g/mol (molecular weight of water). 
        # The assert statement scales this amount by the multiplier for the 
        # current prefix.
        for substance in [None, water]:
            moles = water_stock.get_moles(prefix + 'mol', substance)
            assert moles == pytest.approx((1000 / 18.0153) / mult)

        # These substances are not in the water stock, so their moles should be
        # zero.
        for substance in [salt, sodium_sulfate]:
            moles = water_stock.get_moles(prefix + 'mol', substance)
            assert moles == 0

def test_Container_get_volume(empty_container, water, salt, sodium_sulfate, 
                              water_stock):
    """
    Unit Test for `Container.get_volume()`

    This unit test checks the following failure scenarios:
    - Invalid argument types result in raising a `TypeError`
    - Invalid value for 'unit' results in raising a `ValueError`

    This unit test checks for the following success scenarios:
    - Valid unit provided for empty container (with/without substance argument)
    - Valid unit provided for non-empty container (with/without substance argument)
    """

    # ==========================================================================
    # Failure Case: Invalid argument types
    # ==========================================================================
    
    with pytest.raises(TypeError, match="Unit must be a str\\."):
        empty_container.get_volume(None)
    with pytest.raises(TypeError, match="Unit must be a str\\."):
        empty_container.get_volume(789)

    with pytest.raises(TypeError, match="Substance argument must be a Substance or None\\."):
        empty_container.get_volume('L', 789)
    with pytest.raises(TypeError, match="Substance argument must be a Substance or None\\."):
        empty_container.get_volume('L', "invalid")

    # ==========================================================================
    # Failure Case: Invalid value for 'unit'
    # ==========================================================================
    
    # Sub-Case: Non-volume unit (e.g. 'g' or 'mol' or any invalid unit)
    with pytest.raises(ValueError, match="Invalid volume unit "):
        empty_container.get_volume('g')
    with pytest.raises(ValueError, match="Invalid volume unit "):
        empty_container.get_volume('mol')
    with pytest.raises(ValueError, match="Invalid volume unit "):
        empty_container.get_volume('2 g')
    for unit in test_invalid_units:
        with pytest.raises(ValueError, match="Invalid volume unit "):
            empty_container.get_volume(unit)

    # Sub-Case: Invalid unit values (satisfy 'L' end check)
    with pytest.raises(ValueError):
        empty_container.get_volume('jL')
    with pytest.raises(ValueError):
        empty_container.get_volume('wegmolL')
    with pytest.raises(ValueError):
        empty_container.get_volume('10 L')

    
    # ==========================================================================
    # Success Case: Empty container
    # ==========================================================================
    
    for prefix in test_prefixes:
        for substance in [None, water, salt, sodium_sulfate]:
            volume = empty_container.get_volume(prefix + 'L', substance)
            assert volume == 0


    # ==========================================================================
    # Success Case: Non-empty container
    # ==========================================================================
    
    for prefix, mult in zip(test_prefixes, test_prefix_multipliers):
        # Fixture is created with 1 L of water. Thus, both total volume and 
        # water volume should be 1 L. The assert statement scales this amount 
        # by the multiplier for the current prefix.
        for substance in [None, water]:
            volume = water_stock.get_volume(prefix + 'L', substance)
            assert volume == pytest.approx(1 / mult, rel=1e-10)

        # These substances are not in the water stock, so their volumes should 
        # be zero.
        for substance in [salt, sodium_sulfate]:
            volume = water_stock.get_volume(prefix + 'L', substance)
            assert volume == 0

def test_Container_get_quantity(empty_container, water, salt, sodium_sulfate):
    """
    Unit Test for `Container.get_quantity()`

    This unit test checks the following failure scenarios:
    - Invalid argument types result in raising a `TypeError`
    - Invalid value for 'unit' results in raising a `ValueError`

    This unit test checks for the following success scenarios:
    - Valid unit provided for empty container (with/without substance argument)
    - Valid unit provided for non-empty container (with/without substance argument)
    """

    # ==========================================================================
    # Failure Case: Invalid argument types
    # ==========================================================================
    
    with pytest.raises(TypeError, match="Unit must be a str\\."):
        empty_container.get_quantity(None)
    with pytest.raises(TypeError, match="Unit must be a str\\."):
        empty_container.get_quantity(789)

    with pytest.raises(TypeError, match="Substance argument must be a Substance or None\\."):
        empty_container.get_quantity('L', 789)
    with pytest.raises(TypeError, match="Substance argument must be a Substance or None\\."):
        empty_container.get_quantity('L', "invalid")

    # ==========================================================================
    # Failure Case: Invalid value for 'unit'
    # ==========================================================================

    # Check invalid unit permutations
    for unit in test_invalid_units:
        with pytest.raises(ValueError):
            empty_container.get_quantity(unit)

    # Additional handwritten test examples
    test_examples = [
        '', '  ', '\t', '\n',
        'jg', 'jmol', 'jL',
        'abba', 'asdfg', 
        '10g', '10mol', '10L', 
        '10 g', '10 mol', '10 L', 
    ]

    for ex in test_examples:
        with pytest.raises(ValueError):
            empty_container.get_quantity(ex)

    
    # ==========================================================================
    # Success Case: Empty container
    # ==========================================================================
    
    for unit in test_units:
        for substance in [None, water, salt, sodium_sulfate]:
            volume = empty_container.get_quantity(unit, substance)
            assert volume == 0


    # ==========================================================================
    # Success Case: Non-empty container
    # ==========================================================================
    
    for unit in test_units:
        # To avoid all the extra unit conversions for each possibile unit, 
        # create a custom water stock with a known amount of water in the 
        # unit being tested.
        custom_water_stock = Container('water stock', 
                                       initial_contents=[(water, f"5 {unit}")])

        for substance in [None, water]:
            volume = custom_water_stock.get_quantity(unit, substance)
            assert volume == pytest.approx(5, rel=1e-6)

        # These substances are not in the water stock, so their volumes should 
        # be zero.
        for substance in [salt, sodium_sulfate]:
            volume = custom_water_stock.get_quantity(unit, substance)
            assert volume == 0

def test_Container_get_concentration(water, salt):
    """
    Unit Test for `Container.get_concentration()`.

    This unit test checks the following failure scenarios:
    - Invalid argument types result in raising a `TypeError`
    - Invalid argument value for 'unit' results in raising a `ValueError`

    This unit test checks the following success scenarios:
    - The method returns 0 if the substance is not in the container.
    - The method returns the correct concentration of the substance in the 
      container in the specified units.
      - Units tested: ['M', 'L/L', 'mL/L', 'mol/mol', 'mol/mmol']
    """

    container = Container('container', '10 mL')
    
    # ==========================================================================
    # Failure Case: Invalid argument types
    # ==========================================================================

    with pytest.raises(TypeError, match='Solute must be a Substance'):
        container.get_concentration('water')
    
    with pytest.raises(TypeError, match='Unit must be a str'):
        container.get_concentration(water, None)
    with pytest.raises(TypeError, match='Unit must be a str'):
        container.get_concentration(water, 1)


    # ==========================================================================
    # Failure Case: Invalid argument value - invalid unit
    # ==========================================================================

    for unit in test_invalid_units:
        with pytest.raises(ValueError):
            container.get_concentration(salt, unit)


    # ==========================================================================
    # Success Case: Substance is not in the container 
    # ==========================================================================
    
    assert salt not in container.contents
    conc = container.get_concentration(salt, 'M')
    assert conc == 0


    # ==========================================================================
    # Success Case: Substance is in the container
    # ==========================================================================
    
    # Density is set to match water, and molar mass is set to 1 to simplify 
    # conversions. 
    simple_solute = Substance.solid('simple', 1, 0.001)

    # Check if the method returns the correct concentration of the substance in 
    # the container (units: M)
    for value in [0.01, 0.1, 0.25, 0.5, 0.75]:
        # Add 'value' liters of solute and '1 - value' liters of water to the
        # solution. This results in 1 L of solution, with 'value' moles of 
        # solute.
        test_container = Container('tc', 'inf L', 
                                   [(simple_solute, str(value) + ' L'),
                                    (water, str(1 - value) + ' L')])
        assert test_container.get_concentration(simple_solute) == \
                pytest.approx(value, abs=1e-3)
        assert test_container.get_concentration(simple_solute, 'L/L') == \
                pytest.approx(value, abs=1e-3)
        assert test_container.get_concentration(simple_solute, 'mL/L') == \
                pytest.approx(value*1000, abs=1e-3)
        

    # Check if the method returns the correct conconcentration of the substance
    # in the container (units: mol/mol)
    for value in [0.01, 0.1, 0.25, 0.5, 0.75]:
        # Add 'value' liters of solute and '1 - value' liters of water to the
        # solution. This results in 1 L of solution, with 'value' moles of 
        # solute.
        test_container = Container('tc', 'inf L', 
                                   [(salt, str(value) + ' mol'),
                                    (water, str(1 - value) + ' mol')])
        assert test_container.get_concentration(salt, 'mol/mol') == \
                pytest.approx(value, abs=1e-3)
        assert test_container.get_concentration(salt, 'mol/mmol') == \
                pytest.approx(value*0.001, abs=1e-3)

    # TODO: Add additional success cases for more unit variations

def test_Container__add(mocker, empty_container, salt):
    """
    Unit Test for `Container._add()`

    This unit test ensures that this function raises any errors raised in the 
    sub-call to `Container._self_add()`. It also checks that the destination
    container that is returned is NOT the same Python object as the original 
    container.

    This unit test does NOT fully test the functionality of the hidden function
    `Container._self_add()`.
    """

    # ==========================================================================
    # Failure Case: Invalid argument types for subcall to Container._self_add()
    # ==========================================================================
    
    # Store the true function in a variable so that it can be called later
    real__add = Container._add

    # Set up mock function for Container._add()
    _type_error_message = "THIS IS A TEST TYPE ERROR!"

    def mock__add_type_error(self, source, quantity):
        raise TypeError(_type_error_message)

    # Replace calls to Container.add() with the mock version.
    mocker.patch.object(Container, '_add', mock__add_type_error)
    
    # Check that this function correctly raises any type errors for the keywords
    # generated by the sub-call to Container._compute_solution_contents()
    with pytest.raises(TypeError, match=_type_error_message):
        empty_container._add(salt, '1 g')

    # Revert Container._compute_solution_contents() to its original form
    mocker.patch.object(Container, '_add', 
                                    real__add)
    

    # ==========================================================================
    # Failure Case: Invalid argument values for subcall to Container._self_add()
    # ==========================================================================
    
    # Store the true function in a variable so that it can be called later
    real__add = Container._add

    # Set up mock function for Container._add()
    _value_error_message = "THIS IS A TEST VALUE ERROR!"
    def mock__add_value_error(self, source, quantity):
        raise ValueError(_value_error_message)

    # Replace calls to Container.add() with the mock version.
    mocker.patch.object(Container, '_add', mock__add_value_error)
    
    # Check that this function correctly raises any type errors for the keywords
    # generated by the sub-call to Container._compute_solution_contents()
    with pytest.raises(ValueError, match=_value_error_message):
        empty_container._add(salt, '1 g')

    # Revert Container._compute_solution_contents() to its original form
    mocker.patch.object(Container, '_add', 
                                    real__add)
    

    # ==========================================================================
    # Success Case: Non-zero transfer added quantity
    # ==========================================================================
    
    salt_stock = empty_container._add(salt, '1 mol')
    
    # Ensure the two objects are not the same
    assert salt_stock is not empty_container 
    
    # Ensure that the old object has not been affected by the added salt
    assert salt not in empty_container.contents

    # Ensure that the salt has been added to the new container as expected
    assert salt in salt_stock.contents
    assert salt_stock.contents[salt] == Unit.convert_to_storage(1, 'mol')
    

    # ==========================================================================
    # Success Case: Zero transfer added quantity
    # ==========================================================================
    
    salt_stock = empty_container._add(salt, '0 mol')
    
    # Ensure the two objects are not the same
    assert salt_stock is not empty_container 
    
    # Ensure that the old object has not been affected by the added salt
    assert salt not in empty_container.contents

    # Ensure that salt has not been added to the new container's contents
    assert salt not in salt_stock.contents

def test_Container_transfer(mocker: pytest_mock.MockerFixture, 
                            water_stock, salt_water, empty_plate, water_plate):
    """
    Unit Test for the function `Container.transfer()`
    
    NOTE: There are separate unit tests for the hidden functions `Container._transfer()`
    and `Container._transfer_slice()`. The purpose of this unit test is to ensure that 
    the wrapper function `Container.transfer()` works correctly. 

    This unit test checks the following scenarios:
    - Arguments raise a `TypeError` if they are not the correct types
    - Calling with the correct types with a Container as the source
    - Calling with the correct types with a Plate as the source
    """
    # ==========================================================================
    # Failure Case: Invalid argument types
    # ==========================================================================
    
    with pytest.raises(TypeError, match='Destination must be a Container'):
        Container.transfer(1, 1, '10 mL')
    with pytest.raises(TypeError, match='Destination must be a Container'):
        Container.transfer(1, None, '10 mL')
    with pytest.raises(TypeError, match='Destination must be a Container'):
        Container.transfer(1, [], '10 mL')
    with pytest.raises(TypeError, match='Destination must be a Container\\.' + \
                                    ' Use \'Plate\\.transfer\\(\\)\' to transfer' + \
                                    ' to a Plate\\.'):
        Container.transfer(1, empty_plate, '10 mL')
    with pytest.raises(TypeError, match='Destination must be a Container\\.' + \
                                    ' Use \'Plate\\.transfer\\(\\)\' to transfer' + \
                                    ' to a Plate\\.'):
        Container.transfer(1, water_plate, '10 mL')
    with pytest.raises(TypeError, match='Invalid source type'):
        Container.transfer(1, water_stock, '10 mL')


    # ==========================================================================
    # Success Cases
    # ==========================================================================    

    _transfer_message = "SUCCESSFUL CALL TO 'Container._transfer()'!"
    _transfer_slice_message = "SUCCESSFUL CALL TO 'Container._transfer_slice()'!"

    # Set up mocking for Container._transfer() and Container._transfer_slice()
    def mock__transfer(container, source, quantity):
        return _transfer_message
    
    def mock__transfer_slice(container, source, quantity):
        return _transfer_slice_message

    # Replace calls to Container._transfer and Container._transfer_slice functions
    # with calls to the mock versions
    mocker.patch.object(Container, '_transfer', mock__transfer)
    mocker.patch.object(Container, '_transfer_slice', mock__transfer_slice)

    # ==========================================
    # Success case: call to _transfer()
    # ==========================================    
    #
    result = Container.transfer(salt_water, water_stock, "1 mL")
    assert result == _transfer_message, \
        "Container.transfer() failed to call Container._transfer()"
    
    result = Container.transfer(water_stock, salt_water, "0.5 L")
    assert result == _transfer_message, \
        "Container.transfer() failed to call Container._transfer()"
    
    # ==========================================
    # Success case: call to _transfer_slice()
    # ==========================================    
    #
    result = Container.transfer(water_plate, water_stock, "50 uL")
    assert result == _transfer_slice_message, \
        "Container.transfer() failed to call Container._transfer_slice()"
    
    result = Container.transfer(water_plate, salt_water, ".25 L")
    assert result == _transfer_slice_message, \
        "Container.transfer() failed to call Container._transfer_slice()"

def test_Container__auto_generate_solution_name(salt, sodium_sulfate, water, 
                                                water_stock, salt_water):
    """
    Unit Test for `Container._auto_generate_solution_name()`

    This unit test checks the following failure scenarios:
    - Invalid argument types result in raising a `TypeError`

    This unit test checks the following success scenarios:
    - Single solute and pure Substance solvent
    - Multiple solutes and pure Substance solvent
    - Single solute and Container solvent with one substance
    - Multiple solutes and Container solvent with one substance
    - Single solute and Container solvent with multiple substances
    """

    # ==========================================================================
    # Failure Case: Invalid argument types
    # ==========================================================================
    
    non_substances = [None, False, 1, 'water', {}, 
                      [1], [water_stock], [salt, 1]]
    for non_substance in non_substances:
        with pytest.raises(TypeError, match=r'Solute\(s\) must be a Substance\.'):
            Container._auto_generate_solution_name(non_substance, water)

    for bad_solvent in [None, False, 1, 'water', [1], [water_stock], {}]:
        with pytest.raises(TypeError, match='Solvent must be a Substance or a Container\\.'):
            Container._auto_generate_solution_name(salt, bad_solvent)

    
    # ==========================================================================
    # Success Case: Single solute and pure Substance solvent
    # ==========================================================================
    auto_name = Container._auto_generate_solution_name(salt, water)
    assert auto_name == "Solution of NaCl in H2O"


    # ==========================================================================
    # Success Case: Multiple solutes and pure Substance solvent
    # ==========================================================================
    
    auto_name = Container._auto_generate_solution_name([salt, sodium_sulfate], 
                                                       water)
    assert auto_name == "Solution of NaCl, Sodium sulfate in H2O"


    # ==========================================================================
    # Success Case: Single solute and Container solvent with one substance
    # ==========================================================================
    
    auto_name = Container._auto_generate_solution_name(salt, water_stock)
    assert auto_name == "Solution of NaCl in H2O"


    # ==========================================================================
    # Success Case: Multiple solutes and Container solvent with one substance
    # ==========================================================================
    
    auto_name = Container._auto_generate_solution_name([salt, sodium_sulfate], 
                                                       water_stock)
    assert auto_name == "Solution of NaCl, Sodium sulfate in H2O"


    # ==========================================================================
    # Success Case: Single solute and Container solvent with multiple substances
    # ==========================================================================
    
    auto_name = Container._auto_generate_solution_name(salt, salt_water)
    assert auto_name == "Solution of NaCl in contents of Container 'salt water'"

def test_Container__compute_solution_contents(water, salt, sodium_sulfate, 
                                              triethylamine, dmso, 
                                              water_stock, salt_water):
    """
    Unit Test for the function `Container._compute_solution_contents()`
    
    This unit test checks the following failure scenarios:
    - Invalid argument types result in raising a `TypeError`.
    - Invalid concentration values result in raising a `ValueError`.
    - Invalid quantity values result in raising a `ValueError`.
    - Invalid total quantity values result in raising a `ValueError`.
    - Invalid number of constraints results in raising a `ValueError`.
    - Matching solute and pure Substance solvent results in raising a 
      `ValueError`.
    - Conflicting constraints results in raising a `ValueError`.
    - Constraints which require negative amounts of solute(s) or solvent 
      to satisfy result in raising a `ValueError`.

    This unit test checks the following success scenarios:
    - Single solute and pure Substance solvent
        - Edge case: Large total quantity specified (1e13 kL)
    - Multiple solutes and pure Substance solvent 
    - Single solute and Container solvent (no overlapping Substances)
    - Multiple solutes and Container solvent (no overlapping Substances)
    - Multiple solutes and Container solvent (overlapping Substances)
    
    For all scenarios, all three allowed combinations of concentration, 
    quantity, and total quantity were tested.
    """

    # Create function alias to reduce horizontal space
    _csc = Container._compute_solution_contents

    # ==========================================================================
    # Failure Case: Invalid argument types
    # ==========================================================================

    non_substances = [None, False, 1, 'water', {}, 
                      [1], [water_stock], [salt, 1]]
    for non_substance in non_substances:
        with pytest.raises(TypeError, match=r'Solutes must be a set of Substances\.'):
            _csc(non_substance, water)

    for bad_solvent in [None, False, 1, 'water', [1], [water_stock], {}]:
        with pytest.raises(TypeError, match='Solvent must be a Substance or a Container\\.'):
            _csc([salt], bad_solvent)

    for bad_concen in [False, 1, water, [1], [], [water_stock], {}]:
        with pytest.raises(TypeError, match=r'Concentration\(s\) must be a str\.'):
            _csc([salt], water, 
                    concentration=bad_concen, 
                    total_quantity='10 mL')
    
    for bad_quantity in [False, 1, water, [1], [], [water_stock], {}]:
        with pytest.raises(TypeError, match=r'Quantity\(s\) must be a str\.'):
            _csc([salt], water, 
                    concentration='0.1 M',
                    quantity=bad_quantity)
            
        with pytest.raises(TypeError, match=r'Total quantity must be a str\.'):
            _csc([salt], water, 
                    concentration='0.1 M',
                    total_quantity=bad_quantity)

    
    # ==========================================================================
    # Failure Case: Invalid solute value - repeated solutes in solute set
    # ==========================================================================
    
    repeated_solutes = [salt, sodium_sulfate, salt]

    with pytest.raises(ValueError, match="Solute substances cannot repeat."):
        _csc(repeated_solutes, water, 
                concentration='0.1 M', 
                total_quantity='100 mL')

    
    # ==========================================================================
    # Failure Case: Invalid concentration value 
    # ==========================================================================

    # Sub-Case: Concentration cannot be parsed (i.e. the call to 
    #           Unit.parse_concentration() raises a ValueError)
    for bad_concen in ['0.1', '0.1 MaM', '0.1 M M', '0.1 M M M', '0.1 L/A',
                       '0.1 mol', '0.1 g', '0.1 L', '12 kmol', '0.1 M/L',
                       'NaN M']:
        with pytest.raises(ValueError, match=r'Invalid concentration \'.*\'\.'):
            _csc([salt], water, 
                concentration=bad_concen,
                total_quantity='10 mL')
            
    # Sub-Case: Concentration value is nonsensical for creating a solution
    
    # Sub-Sub-Case: Concentration is not finite
    match_msg = r'Concentration\(s\) must be finite\.'
    for bad_concen in ['inf M', '-inf M']:
        with pytest.raises(ValueError, match=match_msg):
            _csc([salt], water, 
                    concentration=bad_concen,
                    total_quantity='10 mL')
            
    # Sub-Sub-Case: Concentration is negative
    match_msg = r'Concentration\(s\) must be non-negative\.'
    for bad_concen in ['-1 M', '-0.01 L/L']:
        with pytest.raises(ValueError, match=match_msg):
            _csc([salt], water, 
                    concentration=bad_concen,
                    total_quantity='10 mL')
            

    # Sub-Case: Number of concentrations does not match number of solutes
    #
    # NOTE: The function automatically extends one supplied concentration to 
    # match the number of solutes. 
    match_msg = r'Number of concentrations must match number of solutes\.'

    # Sub-Sub-Case: More concentrations than solutes
    with pytest.raises(ValueError, match=match_msg):
        _csc([salt], water, 
                concentration=('0.1 M', '0.5 M'),
                total_quantity='10 mL')
        
    # Sub-Sub-Case: More solutes than concentrations
    solutes = [salt, sodium_sulfate, triethylamine]
    with pytest.raises(ValueError, match=match_msg):
        _csc(solutes, water, 
                concentration=('0.1 M', '0.5 M'),
                total_quantity='10 mL')


    # ==========================================================================
    # Failure Case: Invalid quantity value  
    # ==========================================================================

    # Sub-Case: Quantity cannot be parsed (i.e. the call to 
    #           Unit.parse_quantity() raises a ValueError)
    for bad_quant in ['0.1', '0.1 Mag', '0.1 mmmol', '0.1 LLLL', '0.1 L/A', 
                       '0.0.1 g', 'NaN g', '1 M', '1 mol/L']:
        with pytest.raises(ValueError, match=r'Invalid quantity \'.*\'\.'):
            _csc([salt], water, 
                    quantity=bad_quant,
                    total_quantity='10 mL')
            
    # Sub-Case: Quantity value is nonsensical for creating a solution
    
    # Sub-Sub-Case: Quantity is not finite
    match_msg = r'Quantity\(s\) must be finite\.'
    for bad_quantity in ['inf g', '-inf g']:
        with pytest.raises(ValueError, match=match_msg):
            _csc([salt], water, 
                quantity=bad_quantity,
                total_quantity='10 mL')
            
    # Sub-Sub-Case: Quantity is negative
    match_msg = r'Quantity\(s\) must be non-negative\.'
    for bad_quantity in ['-1 mol', '-0.01 L']:
        with pytest.raises(ValueError, match=match_msg):
            _csc([salt], water, 
                quantity=bad_quantity,
                total_quantity='10 mL')

    # Sub-Case: Number of quantities does not match number of solutes
    #
    # NOTE: The function automatically extends one supplied quantity to 
    # match the number of solutes. 
    match_msg = r'Number of quantities must match number of solutes\.'

    # Sub-Sub-Case: More quantities than solutes
    with pytest.raises(ValueError, match=match_msg):
        _csc([salt], water, 
                quantity=['1 g', '1 g'],
                total_quantity='10 mL')
        
    # Sub-Sub-Case: More solutes than quantities
    solutes = [salt, sodium_sulfate, triethylamine]
    with pytest.raises(ValueError, match=match_msg):
        _csc(solutes, water, 
                quantity=['1 g', '1 g'],
                total_quantity='10 mL')
        
    
    # ==========================================================================
    # Failure Case: Invalid total quantity value
    # ==========================================================================
    
    # Sub-Case: Total quantity cannot be parsed (i.e. the call to 
    #           Unit.parse_quantity() raises a ValueError)
    for bad_quant in ['0.1', '0.1 Mag', '0.1 mmmol', '0.1 LLLL', '0.1 L/A', 
                       '0.0.1 g', 'NaN g', '1 M', '1 mol/L']:
        with pytest.raises(ValueError, match=r'Invalid total quantity \'.*\'\.'):
            _csc([salt], water, 
                    quantity='1 g',
                    total_quantity=bad_quant)
            
    # Sub-Case: Total quantity value is nonsensical for creating a solution
    
    # Sub-Sub-Case: Total quantity is not finite
    match_msg = r'Total quantity must be finite\.'
    for bad_quantity in ['inf g', '-inf g']:
        with pytest.raises(ValueError, match=match_msg):
            _csc([salt], water, 
                    quantity='1 g',
                    total_quantity=bad_quantity)
            
    # Sub-Sub-Case: Total quantity is negative
    match_msg = r'Total quantity must be non-negative\.'
    for bad_quantity in ['-1 mol', '-0.01 L']:
        with pytest.raises(ValueError, match=match_msg):
            _csc([salt], water, 
                    quantity='1 g',
                    total_quantity=bad_quantity)


    # ==========================================================================
    # Failure Case: Incorrect number of constraints provided
    # ==========================================================================
    
    match_msg = r'Must specify two values out of concentration, quantity, and '\
                r'total quantity\.'

    # Sub-Case: No constraints provided
    with pytest.raises(ValueError, match=match_msg):
        _csc([salt], water)

    # Sub-Case: One constraint provided
    with pytest.raises(ValueError, match=match_msg):
        _csc([salt], water, concentration='0.1M')
    with pytest.raises(ValueError, match=match_msg):
        _csc([salt], water, quantity='1 g')
    with pytest.raises(ValueError, match=match_msg):
        _csc([salt], water, total_quantity='1 g')
        
    # Sub-Case: All constraints provided
    with pytest.raises(ValueError, match=match_msg):
        _csc([salt], water, 
                concentration='0.1 M', 
                quantity='1 g', 
                total_quantity='1 g')
        

    # ==========================================================================
    # Failure Case: Solution constraints cannot all be satisfied
    # ==========================================================================
    
    match_msg = r'Solution is impossible to create. The provided constraints...'

    # Try to create a solution with salt and sodium sulfate such that both the 
    # molar concentration and mass of the two substances are equal (this is
    # impossible because they have different molar masses, so equal masses of 
    # the two implies unequal mole amounts and vice versa). 
    with pytest.raises(ValueError, match=match_msg):
        _csc([salt, sodium_sulfate], water, 
                concentration='1.0 M',
                quantity='1.0 g')
        
    # Edge case: Same as above, but with a very small quantity of each solute
    with pytest.raises(ValueError, match=match_msg):
        _csc([salt, sodium_sulfate], water, 
                concentration='0.1 M',
                quantity='0.001 ng')
    
    
    # ==========================================================================
    # Failure Case: Solution requires negative moles of solute(s) or solvent
    # ==========================================================================
    
    match_msg = r'Solution is impossible to create. Negative amounts...'

    # Try to create pure water from salt and salt water (would require removing
    # the salt from the solution)
    with pytest.raises(ValueError, match=match_msg):
        _csc([salt], salt_water, 
                concentration='0.0 M', 
                total_quantity='1 mL')
    with pytest.raises(ValueError, match=match_msg):
        _csc([salt], salt_water, 
                quantity='0 g', 
                total_quantity='1 mL')
        
    # Try to create a solution where the concentration of a solute is higher
    # than its own density. 
    with pytest.raises(ValueError, match=match_msg):
        _csc([salt], water, 
                concentration='3 g/mL',
                quantity='1.0 g')
        
    
    # ==========================================================================
    # Failure Case: Solute and solvent are the same Substance
    # ==========================================================================
    
    match_msg = r'Solute and solvent cannot be identical\.'
    with pytest.raises(ValueError, match=match_msg):
        _csc([water], water, 
                concentration=f'{water.density} g/mL',
                total_quantity='10 mL')
        

    # ==========================================================================
    # Failure Case: Solvent contents completely overlap with solutes
    # ==========================================================================
    
    match_msg = r'Solvent must contain at least one Substance that is not also'\
                r' a solute.'
    with pytest.raises(ValueError, match=match_msg):
        _csc([salt, water], salt_water, 
                concentration=f'{water.density} g/mL',
                total_quantity='10 mL')


    # The following variables are used in the success cases of this unit test
    solutes = [[salt], [triethylamine], [sodium_sulfate], 
               [salt, sodium_sulfate], [salt, triethylamine]]
    single_solutes = [[salt], [triethylamine], [sodium_sulfate]]
    multi_solutes = [[salt, sodium_sulfate], [salt, triethylamine]]
    pure_solvents = [water, dmso]

    # ==========================================================================
    # Success Cases: Single/Multiple solutes and pure Substance solvent
    # ==========================================================================
    
    # Sub-Case: Concentration and total quantity provided
    for solute, solvent in product(solutes, pure_solvents):
        for numerator, denominator in product(test_base_units, repeat=2):
            moles = _csc(solute, solvent, 
                            concentration=f"0.0001 {numerator}/{denominator}",
                            total_quantity=f"10 mol")
            
            # Check that all contents have positive amounts.
            assert np.all(moles > 0)

            # Check that all contents sum to the expected total quantity. 
            assert np.sum(moles) == pytest.approx(10, rel=1e-12), \
                "Total quantity does not match supplied argument."
            
            # Compute the total quantity of the solution in terms of the 
            # denominator units
            total_qty_denom = 0
            # Convert each solute amount to the denominator units
            for idx, sub in enumerate(solute):
                total_qty_denom += sub.convert(moles[idx], 'mol', 
                                                     denominator)
            # Convert the solvent to the denominator units
            total_qty_denom += solvent.convert(moles[-1], 'mol', denominator)
            
            # Check that each solute has the correct concentration.
            for idx, sub in enumerate(solute):
                qty_numer = sub.convert(moles[idx], 'mol', numerator)
                conc = qty_numer/total_qty_denom
                assert conc == pytest.approx(0.0001, rel=1e-12), \
                    "Solute concentration does not match supplied argument."

    # Edge Case: Very high total quantity
    moles = _csc([salt], water, 
                    concentration='0.5 M',
                    total_quantity='1e13 kL') 
    
    # Check that all contents have positive amounts.
    assert np.all(moles > 0)

    # Check that all contents sum to the expected total quantity.
    total_vol = sum([sub.convert(moles[idx], 'mol', 'L') 
                        for idx, sub in enumerate([salt, water])])
    assert total_vol == pytest.approx(1e16, rel=1e-12), \
            "Total quantity does not match supplied argument."
    
    # Check that the solute has the correct concentration.
    assert moles[0]/total_vol == pytest.approx(0.5, rel=1e-12), \
            "Solute concentration does not match supplied argument."

    # Sub-Case: Quantity and total quantity provided
    for solute, solvent in product(solutes, pure_solvents):
        for quantity_unit in test_base_units:
            moles = _csc(solute, solvent, 
                            quantity=f"1 {quantity_unit}",
                            total_quantity=f"10 {quantity_unit}")
            
            # Check that all contents have positive amounts.
            assert np.all(moles > 0)

            # Add all solute amounts to the total quantity
            total_qty = 0
            for idx, sub in enumerate(solute):
                # Convert each solute amount to the quantity units,
                # check that it matches the supplied constraint.
                qty = sub.convert(moles[idx], 'mol', quantity_unit)
                assert qty == pytest.approx(1, rel=1e-12), \
                    "Solute quantity does not match supplied argument."
                
                total_qty += qty

            # Add the solvent amount to the total quantity
            total_qty += solvent.convert(moles[-1], 'mol', quantity_unit)

            # Check that all contents sum to the expected total quantity. 
            assert total_qty == pytest.approx(10, rel=1e-12), \
                "Total quantity does not match supplied argument."    

    
    test_units_subset = ['g', 'ng', 'Mg', 
                         'mol', 'nmol', 'Mmol', 
                         'L', 'nL', 'ML']
    
    def check_skip_case(solute, val, numerator, denominator):
        """
        Helper function for checking if a case should be skipped due to the
        concentration being greater than the density of the solute.
        """
        for sub in solute:
            num_in_g = sub.convert(val, numerator, 'g')
            denom_in_mL = sub.convert(1, denominator, 'mL')
            if num_in_g / denom_in_mL >= sub.density:
                return True
        return False

    # Sub-Case: Single solute, concentration and quantity provided
    
    # Create variations of solutes, solvents, and units
    substance_variations = cycle(product(single_solutes, pure_solvents))
    unit_variations = product(test_units_subset, repeat=3)
    variations = zip(substance_variations, unit_variations)
    
    for (substances), (units) in variations:
        solute, solvent = substances
        numerator, denominator, quantity_unit = units

        # Check to make sure the concentration is feasible (less than the 
        # density of the solute)
        if check_skip_case(solute, 0.001, numerator, denominator):
            continue    

        moles = _csc(solute, solvent, 
                        concentration=f"0.001 {numerator}/{denominator}",
                        quantity=f"1 {quantity_unit}")

        # Check that all contents have positive amounts.
        assert np.all(moles > 0)

        # Convert each solute amount to the quantity units, and check that
        # it matches the supplied constraint.
        for idx, sub in enumerate(solute):
            qty = sub.convert(moles[idx], 'mol', quantity_unit)
            assert qty == pytest.approx(1, rel=1e-12), \
                "Solute quantity does not match supplied argument."

        # Compute the total quantity of the solution in terms of the 
        # denominator units
        total_qty_denom = 0
        # Convert each solute amount to the denominator units
        for idx, sub in enumerate(solute):
            total_qty_denom += sub.convert(moles[idx], 'mol', 
                                                    denominator)
        # Convert the solvent to the denominator units
        total_qty_denom += solvent.convert(moles[-1], 'mol', denominator)
        
        # Check that each solute has the correct concentration.
        for idx, sub in enumerate(solute):
            qty_numer = sub.convert(moles[idx], 'mol', numerator)
            conc = qty_numer/total_qty_denom
            assert conc == pytest.approx(0.001, rel=1e-12), \
                "Solute concentration does not match supplied argument." 
    
    # Sub-Case: Multiple solutes, concentration and quantity provided
    # 
    # NOTE: Constraints must form a linearly dependent system to be solvable.
    #       Constraints which fail to do so are handled in the failure cases.
    
    # Create variations of solutes, solvents, and units
    substance_variations = cycle(product(multi_solutes, pure_solvents))
    unit_variations = product(test_units_subset, repeat=3)
    variations = zip(substance_variations, unit_variations)

    for (substances), (units) in variations:
        solute, solvent = substances
        numerator, denominator, quantity_unit = units
        
        # Compute the ratios of the 'quantity unit per mole' properties of 
        # the solutes 
        qty_ratios = [sub.convert(1, numerator, quantity_unit) / 
                    solute[0].convert(1, denominator, quantity_unit) \
                    for sub in solute]
        qty_vals = [1 * ratio for ratio in qty_ratios]
        quantities = [f"{val} {quantity_unit}" for val in qty_vals]

        # Check to make sure the concentration is feasible (less than the 
        # density of the solute)
        if check_skip_case(solute, 0.001, numerator, denominator):
            continue  

        moles = _csc(solute, solvent, 
                        concentration=f"0.001 {numerator}/{denominator}",
                        quantity=quantities)
        
        # Check that all contents have positive amounts.
        assert np.all(moles > 0)

        # Convert each solute amount to the quantity units, and check that
        # it matches the supplied constraint.
        for idx, sub in enumerate(solute):
            qty = sub.convert(moles[idx], 'mol', quantity_unit)
            assert qty == pytest.approx(qty_vals[idx], rel=1e-12), \
                "Solute quantity does not match supplied argument."

        # Compute the total quantity of the solution in terms of the 
        # denominator units
        total_qty_denom = 0
        # Convert each solute amount to the denominator units
        for idx, sub in enumerate(solute):
            total_qty_denom += sub.convert(moles[idx], 'mol', 
                                                    denominator)
        # Convert the solvent to the denominator units
        total_qty_denom += solvent.convert(moles[-1], 'mol', denominator)
        
        # Check that each solute has the correct concentration.
        for idx, sub in enumerate(solute):
            qty_numer = sub.convert(moles[idx], 'mol', numerator)
            conc = qty_numer/total_qty_denom
            assert conc == pytest.approx(0.001, rel=1e-12), \
                "Solute concentration does not match supplied argument." 
    

    # ==========================================================================
    # Success Cases: Single/Multiple solutes and Container solvent (no 
    #                overlapping Substances)
    # ==========================================================================

    # Sub-Case: Concentration and total quantity provided
    for solute, solvent in product(solutes, [water_stock]):
        for numerator, denominator in product(test_base_units, repeat=2):
            moles = _csc(solute, solvent, 
                            concentration=f"0.0001 {numerator}/{denominator}",
                            total_quantity=f"10 mol")
            
            # Check that all contents have positive amounts.
            assert np.all(moles > 0)

            # Check that all contents sum to the expected total quantity. 
            assert np.sum(moles) == pytest.approx(10, rel=1e-12), \
                "Total quantity does not match supplied argument."
            
            # Compute the total quantity of the solution in terms of the 
            # denominator units
            total_qty_denom = 0
            
            # Convert each solute amount to the denominator units
            for idx, sub in enumerate(solute):
                total_qty_denom += sub.convert(moles[idx], 'mol', 
                                                     denominator)
                      
            # Compute the total contents of the solvent in storage units
            total_solvent_amt = sum(val for val in solvent.contents.values())
            # Compute the mole fraction of each substance in the solvent.
            sub_frac_in_solvent = {}
            for sub, val in solvent.contents.items():
                sub_frac_in_solvent[sub] = val / total_solvent_amt
            
            # Convert the transfer amount of each substance in the solvent 
            # Container into the denominator units
            for sub in solvent.contents.keys():
                # Compute the mole amount of each substance that will be 
                # transferred from the solvent to the new solution.
                transfer_moles = sub_frac_in_solvent[sub] * moles[-1]

                # Convert the mole amount to the denominator units
                transfer_qty = sub.convert(transfer_moles, 'mol', denominator)

                total_qty_denom += transfer_qty

            # Check that each solute has the correct concentration.
            for idx, sub in enumerate(solute):
                # Compute the pure solute's contrbution to the numerator
                qty_numer = sub.convert(moles[idx], 'mol', numerator)
                
                # Add the solvent's contribution to the numerator
                mole_frac = sub_frac_in_solvent.get(sub, 0)
                qty_numer += sub.convert(mole_frac * moles[-1], 'mol', numerator)

                # Compute the concentration of the solute and check if it 
                # matches the supplied argument.
                conc = qty_numer/total_qty_denom
                assert conc == pytest.approx(0.0001, rel=1e-12), \
                    "Solute concentration does not match supplied argument."

    # Sub-Case: Quantity and total quantity provided            
    for solute, solvent in product(solutes, [water_stock]):
        for quantity_unit in test_base_units:
            moles = _csc(solute, solvent, 
                            quantity=f"1 {quantity_unit}",
                            total_quantity=f"10 {quantity_unit}")
            
            # Check that all contents have positive amounts.
            assert np.all(moles > 0)

            # Add all solute amounts to the total quantity
            total_qty = 0
            for idx, sub in enumerate(solute):
                # Convert each solute amount to the quantity units, and
                # check that it matches the supplied constraint.
                qty = sub.convert(moles[idx], 'mol', quantity_unit)
                assert qty == pytest.approx(1, rel=1e-12), \
                    "Solute quantity does not match supplied argument."
                
                total_qty += qty

            # Add the solvent amount to the total quantity

            # Compute the total contents of the solvent in storage units
            total_solvent_amt = sum(val for val in solvent.contents.values())
            # Compute the mole fraction of each substance in the solvent.
            sub_frac_in_solvent = {}
            for sub, val in solvent.contents.items():
                sub_frac_in_solvent[sub] = val / total_solvent_amt
            
            # Convert the transfer amount of each substance in the solvent 
            # Container into the quantity unit
            for sub in solvent.contents.keys():
                # Compute the mole amount of each substance that will be 
                # transferred from the solvent to the new solution.
                transfer_moles = sub_frac_in_solvent[sub] * moles[-1]

                # Convert the transfer mole amount to the quantity unit
                transfer_qty = sub.convert(transfer_moles, 'mol', quantity_unit)

                # Add the transfer amount to the total quantity
                total_qty += transfer_qty

            # Check that all contents sum to the expected total quantity. 
            assert total_qty == pytest.approx(10, rel=1e-10), \
                "Total quantity does not match supplied argument."         
    
    # Sub-Case: Single solute, concentration and quantity provided
    
    # Create variations of solutes, solvents, and units
    substance_variations = cycle(product(single_solutes, [water_stock]))
    unit_variations = product(test_units_subset, repeat=3)
    variations = zip(substance_variations, unit_variations)
    
    for (substances), (units) in variations:
        solute, solvent = substances
        numerator, denominator, quantity_unit = units
            
        # Check to make sure the concentration is feasible (less than the 
        # density of the solute)
        if check_skip_case(solute, 0.001, numerator, denominator):
            continue  

        moles = _csc(solute, solvent, 
                        concentration=f"0.001 {numerator}/{denominator}",
                        quantity=f"1 {quantity_unit}")

        # Check that all contents have positive amounts.
        assert np.all(moles > 0)

        # Convert each solute amount to the quantity units, and check that
        # it matches the supplied constraint.
        for idx, sub in enumerate(solute):
            qty = sub.convert(moles[idx], 'mol', quantity_unit)
            assert qty == pytest.approx(1, rel=1e-12), \
                "Solute quantity does not match supplied argument."

        # Compute the total quantity of the solution in terms of the 
        # denominator units
        total_qty_denom = 0
        # Convert each solute amount to the denominator units
        for idx, sub in enumerate(solute):
            total_qty_denom += sub.convert(moles[idx], 'mol', 
                                                    denominator)
        
        # Compute the total contents of the solvent in storage units
        total_solvent_amt = sum(val for val in solvent.contents.values())
        # Compute the mole fraction of each substance in the solvent.
        sub_frac_in_solvent = {}
        for sub, val in solvent.contents.items():
            sub_frac_in_solvent[sub] = val / total_solvent_amt
        
        # Convert the transfer amount of each substance in the solvent 
        # Container into the denominator units
        for sub in solvent.contents.keys():
            # Compute the mole amount of each substance that will be 
            # transferred from the solvent to the new solution.
            transfer_moles = sub_frac_in_solvent[sub] * moles[-1]

            # Convert the mole amount to the denominator units
            transfer_qty = sub.convert(transfer_moles, 'mol', denominator)

            total_qty_denom += transfer_qty
        
        # Check that each solute has the correct concentration.
        for idx, sub in enumerate(solute):
            # Compute the pure solute's contrbution to the numerator
            qty_numer = sub.convert(moles[idx], 'mol', numerator)
            
            # Add the solvent's contribution to the numerator
            mole_frac = sub_frac_in_solvent.get(sub, 0)
            qty_numer += sub.convert(mole_frac * moles[-1], 'mol', numerator)

            # Compute the concentration of the solute and check if it 
            # matches the supplied argument.
            conc = qty_numer/total_qty_denom
            assert conc == pytest.approx(0.001, rel=1e-12), \
                "Solute concentration does not match supplied argument."
    
    # Sub-Case: Multiple solutes, concentration and quantity provided
    # 
    # NOTE: Constraints must form a linearly dependent system to be solvable.
    #       Constraints which fail to do so are handled in the failure cases.
    
    # Create variations of solutes, solvents, and units
    substance_variations = cycle(product(multi_solutes, [water_stock]))
    unit_variations = product(test_units_subset, repeat=3)
    variations = zip(substance_variations, unit_variations)
    
    for (substances), (units) in variations:
        solute, solvent = substances
        numerator, denominator, quantity_unit = units
        
        # Compute the ratios of the 'quantity unit per mole' properties of 
        # the solutes 
        qty_ratios = [sub.convert(1, numerator, quantity_unit) / 
                    solute[0].convert(1, denominator, quantity_unit) \
                    for sub in solute]
        qty_vals = [1 * ratio for ratio in qty_ratios]
        quantities = [f"{val} {quantity_unit}" for val in qty_vals]

        # Check to make sure the concentration is feasible (less than the 
        # density of the solute)
        if check_skip_case(solute, 0.001, numerator, denominator):
            continue  

        moles = _csc(solute, solvent, 
                        concentration=f"0.001 {numerator}/{denominator}",
                        quantity=quantities)

        # Check that all contents have positive amounts.
        assert np.all(moles > 0)

        # Convert each solute amount to the quantity units, and check that
        # it matches the supplied constraint.
        for idx, sub in enumerate(solute):
            qty = sub.convert(moles[idx], 'mol', quantity_unit)
            assert qty == pytest.approx(qty_vals[idx], rel=1e-12), \
                "Solute quantity does not match supplied argument."

        # Compute the total quantity of the solution in terms of the 
        # denominator units
        total_qty_denom = 0
        # Convert each solute amount to the denominator units
        for idx, sub in enumerate(solute):
            total_qty_denom += sub.convert(moles[idx], 'mol', 
                                                    denominator)
        
        # Compute the total contents of the solvent in storage units
        total_solvent_amt = sum(val for val in solvent.contents.values())
        # Compute the mole fraction of each substance in the solvent.
        sub_frac_in_solvent = {}
        for sub, val in solvent.contents.items():
            sub_frac_in_solvent[sub] = val / total_solvent_amt
        
        # Convert the transfer amount of each substance in the solvent 
        # Container into the denominator units
        for sub in solvent.contents.keys():
            # Compute the mole amount of each substance that will be 
            # transferred from the solvent to the new solution.
            transfer_moles = sub_frac_in_solvent[sub] * moles[-1]

            # Convert the mole amount to the denominator units
            transfer_qty = sub.convert(transfer_moles, 'mol', denominator)

            total_qty_denom += transfer_qty
        
        # Check that each solute has the correct concentration.
        for idx, sub in enumerate(solute):
            # Compute the pure solute's contrbution to the numerator
            qty_numer = sub.convert(moles[idx], 'mol', numerator)
            
            # Add the solvent's contribution to the numerator
            mole_frac = sub_frac_in_solvent.get(sub, 0)
            qty_numer += sub.convert(mole_frac * moles[-1], 'mol', numerator)

            # Compute the concentration of the solute and check if it 
            # matches the supplied argument.
            conc = qty_numer/total_qty_denom
            assert conc == pytest.approx(0.001, rel=1e-12), \
                "Solute concentration does not match supplied argument." 
    

    # ==========================================================================
    # Success Case: Multiple solutes and Container solvent (overlapping 
    #               Substances with solute)
    # ==========================================================================

    test_solutes = [[salt, sodium_sulfate],
                    [salt, triethylamine]]

    for test_solute in test_solutes:
        moles = _csc(test_solute, salt_water,
                        concentration=['1.0 M', '0.001 M'],
                        total_quantity='10 mol')
        
        # Check that all contents have positive amounts.
        assert np.all(moles > 0)

        # Check that all contents sum to the expected total quantity.
        assert np.sum(moles) == pytest.approx(10, rel=1e-12), \
            f"Total quantity does not match supplied argument. {np.sum(moles)}"

        # Compute the total quantity of the solution in terms of 'L'
        total_qty_L = 0
        # Convert each solute amount to 'L'
        for idx, sub in enumerate(test_solute):
            total_qty_L += sub.convert(moles[idx], 'mol', 'L')
        
        # Compute the total contents of the solvent in storage units
        total_solvent_amt = sum(val for val in salt_water.contents.values())
        # Compute the mole fraction of each substance in the solvent.
        sub_frac_in_solvent = {}
        for sub, val in salt_water.contents.items():
            sub_frac_in_solvent[sub] = val / total_solvent_amt
        
        # Convert the transfer amount of each substance in the solvent 
        # Container into the denominator units ('L')
        for sub in salt_water.contents.keys():
            # Compute the mole amount of each substance that will be 
            # transferred from the solvent to the new solution.
            transfer_moles = sub_frac_in_solvent[sub] * moles[-1]

            # Convert the mole amount to the denominator units ('L') and add it to
            # the total quantity
            total_qty_L += sub.convert(transfer_moles, 'mol', 'L')


        # Check that each solute has the correct concentration.
        for (idx, sub), expected_conc in zip(enumerate(test_solute), [1, 0.001]):
            # Compute the pure solute's contrbution to the numerator
            qty_numer = moles[idx]
            
            # Add the solvent's contribution to the numerator
            mole_frac = sub_frac_in_solvent.get(sub, 0)
            qty_numer += mole_frac * moles[-1]

            # Compute the concentration of the solute and check if it 
            # matches the supplied argument.
            # TODO: Potentially fix precision issue here
            conc = qty_numer / total_qty_L
            assert conc == pytest.approx(expected_conc, rel=1e-10), \
                f"Solute concentration does not match supplied argument. {conc} M"

def test_Container_create_solution(mocker: pytest_mock.MockerFixture, 
                                   water, dmso, salt, triethylamine, 
                                   sodium_sulfate, water_stock):
    """
    Unit Test for the function `Container.create_solution()`

    This unit test checks the following failure scenarios:
    - Invalid argument types will result in raising a `TypeError`
    - Invalid argument values will result in raising a `ValueError`.

    This unit test checks the following success scenarios:
    - Single solute and pure Substance solvent (various units)
    - Multiple solutes and pure Substance solvent (various units)
    - Single solute and Container solvent (specific units)
    - Multiple solutes and Container solvent (specific units)

    In each success case, the resulting solution is checked to see if the 
    properties match the provided constraints. If a solvent Container is used,
    as part of the success case, it is checked to ensure the volume has been 
    reduced by the correct amount.

    This unit test depends on the correctness of the following functions:
    - `Container.get_concentration()`
    - `Container.get_quantity()`
    - `Substance.convert()`
    - `Unit.parse_prefixed_unit()` (indirectly)

    TODO: Include checks for proper instruction generation.
    """
    
    # ==========================================================================
    # Failure Case: Invalid argument types (non-keyword)
    # ==========================================================================

    # Solute type checking
    match_msg = r'Solute must be a Substance or an iterable set of Substances\.'
    non_substances = [None, False, 1, 'water', {}, 
                      [1], [water_stock], [salt, 1]]
    for non_substance in non_substances:
        with pytest.raises(TypeError, match=match_msg):
            Container.create_solution(non_substance, water, 
                                      concentration='0.5 M', 
                                      total_quantity='100 mL')
    
    # Solvent type checking
    match_msg = r'Solvent must be a Substance or a Container\.'
    for bad_solvent in [None, False, 1, 'water', [1], [water_stock], {}]:
        with pytest.raises(TypeError, match=match_msg):
            Container.create_solution(salt, bad_solvent, 
                                      concentration='0.5 M', 
                                      total_quantity='100 mL')
    
    # Name type checking (NOTE: None and "" are both valid, as they are intended
    # to be converted to an auto-generated name)
    for non_str in [False, 1, 1.0, [], {}, [1.0], ['1']]:
        with pytest.raises(TypeError, match='Name must be a str\\.'):
            Container.create_solution(salt, water, non_str, 
                                      conventration='0.5 M', 
                                      total_quantity='100 mL')


    # ==========================================================================
    # Failure Case: Invalid argument types (keyword)
    # ==========================================================================
    
    # Store the true function in a variable so that it can be called later
    real_compute_solution_contents = Container._compute_solution_contents

    # Set up mock function for Container._compute_solution_contents()
    _type_error_message = "THIS IS A TEST TYPE ERROR!"

    def mock_compute_type_error(solute, solvent, **kwargs):
        raise TypeError(_type_error_message)

    # Replace calls to Container._compute_solution_contents() with the mock
    # version.
    mocker.patch.object(Container, '_compute_solution_contents', 
                                    mock_compute_type_error)
    
    # Check that this function correctly raises any type errors for the keywords
    # generated by the sub-call to Container._compute_solution_contents()
    with pytest.raises(TypeError, match=_type_error_message):
        Container.create_solution(salt, water)

    # Revert Container._compute_solution_contents() to its original form
    mocker.patch.object(Container, '_compute_solution_contents', 
                                    real_compute_solution_contents)


    # ==========================================================================
    # Failure Case: Invalid argument values (non-keyword and keyword)
    # ==========================================================================

    _value_error_message = "THIS IS A TEST VALUE ERROR!"

    # Set up mock function for Container._compute_solution_contents()
    def mock_compute_value_error(solute, solvent, **kwargs):
        raise ValueError(_value_error_message)
    
    # Replace calls to Container._compute_solution_contents() with the mock
    # version.
    mocker.patch.object(Container, '_compute_solution_contents', 
                                    mock_compute_value_error)

    # Check that this function correctly raises any value errors generated by 
    # the subcall to Container._compute_solution_contents()
    with pytest.raises(ValueError, match=_value_error_message):
        Container.create_solution(salt, water)

    # Revert Container._compute_solution_contents() to its original form
    mocker.patch.object(Container, '_compute_solution_contents', 
                                    real_compute_solution_contents)
    

    
    # The following variables are used in the success cases of this unit test
    solvents = [water, dmso]
    solutes = [salt, triethylamine, sodium_sulfate]
    units = ['g', 'mol', 'mL']


    # ==========================================================================
    # Success Case: Create solution with one solute and Substance solvent
    # ==========================================================================

    # Create a solution using 'concentration' and 'total quantity' parameters
    for numerator, denominator, quantity_unit in product(units, repeat=3):
        for solute in solutes:
            for solvent in solvents:
                # Create a solution with the 'value unit/unit' format for concentration.
                con = Container.create_solution(solute, solvent, 
                                                concentration=f"0.001 {numerator}/{denominator}",
                                                total_quantity=f"10 {quantity_unit}")
                
                # Check that all contents have positive amounts
                assert all(value > 0 for value in con.contents.values()), \
                    f"Making 10 {quantity_unit} of a 0.001 {numerator}/{denominator}" \
                    f" solution of {solute} and {solvent} failed."

                # Check that all contents sum to the expected total quantity 
                total = sum(substance.convert(value, config.moles_storage_unit, quantity_unit) 
                                for substance, value in con.contents.items())
                assert abs(total - 10) < epsilon, \
                    "Total quantity does not match supplied argument."
                
                # Check that the solute has the correct concentration
                conc = con.get_concentration(solute, f"{numerator}/{denominator}")
                assert abs(conc - 0.001) < epsilon, \
                    "Solute concentration does not match supplied argument."


                # Create a solution with the 'value unit/value unit' format for concentration.
                con = Container.create_solution(solute, solvent, concentration=f"0.01 {numerator}/10 {denominator}",
                                                total_quantity=f"10 {quantity_unit}")
                
                # Check that all contents have positive amounts
                assert all(value > 0 for value in con.contents.values()), \
                    f"Making 10 {quantity_unit} of a 0.01 {numerator}/10 {denominator}" \
                    f" solution of {solute} and {solvent} failed."

                # Check that all contents sum to the expected total quantity
                total = sum(substance.convert(value, config.moles_storage_unit, quantity_unit) 
                                for substance, value in con.contents.items())
                assert abs(total - 10) < epsilon, \
                    "Total quantity does not match supplied argument."

                # Check that the solute has the correct concentration.
                conc = con.get_concentration(solute, f"{numerator}/{denominator}")
                assert abs(conc - 0.01/10) < epsilon, \
                    "Solute concentration does not match supplied argument."
                
    # Create a solution using 'quantity' and 'total quantity' parameters
    for amt, quantity_unit in product([1,2,5], units):
        for solute in solutes:
            for solvent in solvents:
                # Create a solution using a quantity of {amt} {quantity_unit} 
                # for each solute and a total quantity of {5 * amt} {quantity_unit}.
                con = Container.create_solution(solute, solvent, 
                                                quantity=[f"{amt} {quantity_unit}"],
                                                total_quantity=f"{5*amt} {quantity_unit}")
                
                # Check that all contents have positive amounts
                assert all(value > 0 for value in con.contents.values()), \
                    f"Making a 5 {quantity_unit} solution of {solute} in {solvent}"\
                        f" with 1 {quantity_unit} of {solute} failed."

                # Check that all contents sum to the expected total quantity 
                total = sum(substance.convert(value, config.moles_storage_unit, quantity_unit) 
                                for substance, value in con.contents.items())
                assert abs(total - amt*5) < epsilon, \
                        "Total quantity does not match supplied argument."
                
                # Check that the solute has the correct quantity
                qty = con.get_quantity(quantity_unit, substance=solute)
                assert abs(qty - amt) < epsilon, \
                    f"{solute} quantity does not match supplied argument."
                
    # Create a solution using 'concentration' and 'quantity' parameters
    for numerator, denominator, quantity_unit in product(units, repeat=3):
        for solute in solutes:
            for solvent in solvents:
                # Create a solution using a quantity of 1 {quantity_unit} 
                # for each solute that has a concentration of 0.001 {numerator}/ 
                # {denominator}.
                con = Container.create_solution(solute, solvent, 
                                                concentration=[f"0.001 {numerator}/{denominator}"],
                                                quantity=[f"1 {quantity_unit}"])
                
                # Check that all contents have positive amounts
                assert all(value > 0 for value in con.contents.values()), \
                    f"Failed to make a 0.001 {numerator}/{denominator} solution of " \
                    f"{solute} and {solvent} with 1 {quantity_unit} of {solute}."
                
                # Check that the solute has the correct concentration.
                conc = con.get_concentration(solute, f"{numerator}/{denominator}")
                assert abs(conc - 0.001) < epsilon, \
                    f"{solute} concentration does not match supplied argument."

                # Check that the solute has the correct quantity.
                qty = con.get_quantity(quantity_unit, substance=solute)
                assert abs(qty - 1) < epsilon, \
                    f"{solute} quantity does not match supplied argument."


    # ==========================================================================
    # Success Case: Create solution from multiple solutes and Substance solvent
    # ==========================================================================

    # Create a solution using 'concentration' and 'total quantity' parameters
    for numerator, denominator, quantity_unit in product(units, repeat=3):
        for solvent in solvents:
            # Create a solution with the 'value unit/unit' format for concentration.
            con = Container.create_solution(solutes, solvent, 
                                            concentration=f"0.001 {numerator}/{denominator}",
                                            total_quantity=f"10 {quantity_unit}")
            
            # Check that all contents have positive amounts
            assert all(value > 0 for value in con.contents.values()), \
                f"Making 10 {quantity_unit} of a 0.001 {numerator}/{denominator}" \
                f" solution of {solutes} and {solvent} failed."
            
            # Check that all contents sum to the expected total quantity 
            total = sum(substance.convert(value, config.moles_storage_unit, quantity_unit) 
                            for substance, value in con.contents.items())
            assert abs(total - 10) < epsilon, \
                "Total quantity does not match supplied argument."
            
            # Check that the solutes hav the correct concentrations
            for solute in solutes:
                conc = con.get_concentration(solute, f"{numerator}/{denominator}")
                assert abs(conc - 0.001) < epsilon, \
                    "Solute concentration does not match supplied argument."
            
    # Create a solution using 'quantity' and 'total quantity' parameters
    for quantity_unit in units:
        for solvent in solvents:
            # Create a solution using a quantity of 1 {unit} for each solute
            # and a total quantity of 10 {unit}.
            con = Container.create_solution(solutes, solvent, 
                                            quantity=[f"1 {quantity_unit}",
                                                      f"1 {quantity_unit}", 
                                                      f"1 {quantity_unit}"],
                                            total_quantity=f"10 {quantity_unit}")
            
            # Check that all contents have positive amounts
            assert all(value > 0 for value in con.contents.values()), \
                f"Making a 10 {quantity_unit} solution of {solute} in {solvent}"\
                    f" with 1 {quantity_unit} of each solute failed."

            # Check that all contents sum to the expected total quantity 
            total = sum(substance.convert(value, config.moles_storage_unit, quantity_unit) 
                            for substance, value in con.contents.items())
            assert abs(total - 10) < epsilon, \
                    "Total quantity does not match supplied argument."
            
            # Check that the solutes have the correct quantities
            for solute in solutes:
                qty = con.get_quantity(quantity_unit, substance=solute)
                assert abs(qty - 1) < epsilon, \
                     f"{solute} quantity does not match supplied argument."


    # ==========================================================================
    # Success Case: Create solution from single solute and Container solvent
    # ==========================================================================
    
    water_stock = Container('water stock', initial_contents=(water, '100 L'))

    # Create a solution using 'concentration' and 'quantity' parameters
    for solute in solutes:
        results = Container.create_solution(solute, water_stock, 
                                            concentration=["0.05 M"],
                                            quantity=["50 g"])
        
        # Check that two Containers have been returned
        assert len(results) == 2
        stock_2, con = results
        
        # Check that the solute has the correct concentration.
        conc = con.get_concentration(solute, "M")
        assert abs(conc - 0.05) < epsilon, \
            "Solute concentration does not match supplied argument."

        # Check that the solute has the correct quantity
        expected_qty = solute.convert(50, 'g', config.moles_storage_unit)
        qty = con.contents[solute]
        assert abs(qty - expected_qty) < epsilon, \
                    f"{solute} quantity does not match supplied argument."

        # Check that the new stock solution's volume has been reduced by
        # the correct amount.
        added_water = con.contents[water]
        lost_water = water_stock.contents[water] - stock_2.contents[water]
        assert lost_water == pytest.approx(added_water, rel=1e-12), \
            "Solvent (water) volume was not reduced by the correct amount!"


    # ==========================================================================
    # Success Case: Create solution from multiple solutes and Container solvent
    # ==========================================================================

    # Create a solution using a quantity of 1 g for each solute and a total 
    # quantity of 10 g.
    new_water_stock, con = Container.create_solution(solutes, water_stock, 
                                                        quantity=[f"1 g",
                                                                    f"1 g", 
                                                                    f"1 g"],
                                                        total_quantity=f"10 g")

    # Checkt that the mass difference between the old water container and the
    # new water container is within epsilon of the expected amount (7 grams)
    old_water_mass = water_stock.get_mass()
    new_water_mass = new_water_stock.get_mass()
    assert abs((old_water_mass - new_water_mass) - 7) < epsilon
    
    # Check that all contents of the new container have positive amounts
    assert all(value > 0 for value in con.contents.values()), \
        f"Making 10 grams of a solution of {solutes} in {solvent}"\
            f" with 1 g of each solute failed."

    # Check that all contents of the new container sum to the expected total 
    # quantity 
    total = sum(substance.convert(value, config.moles_storage_unit, 'g') 
                    for substance, value in con.contents.items())
    assert abs(total - 10) < epsilon, \
            "Total quantity does not match supplied argument."
    
    # Check that the solutes have the correct quantities in the new container
    for solute in solutes:
        qty = con.get_mass(unit='g', substance=solute)
        assert abs(qty - 1) < epsilon, \
                f"{solute} quantity does not match supplied argument."
    
def test_Container_create_dilution(mocker: pytest_mock.MockerFixture, 
                                   water: Substance, dmso: Substance, 
                                   salt: Substance, sodium_sulfate: Substance,
                                   water_stock: Container, 
                                   salt_water: Container, 
                                   salt_water_1M: Container, 
                                   salt_water_2M: Container,
                                   brine: Container):
    """
    Unit Test for the function `Container.create_dilution()`

    This unit test checks the following failure scenarios:
    - Invalid argument types will result in raising a `TypeError`
    - Invalid concentration values will result in raising a `ValueError`
    - Invalid total quantity values will result in raising a `ValueError`
    - Providing a solute that is not found in the source container will result
      in raising a `ValueError`
    - Invalid units encountered during the dilution computations will result in
      raising a `ValueError` (scenario requires mocking to reach)
    - Impossible dilutions will result in raising a `ValueError`
        - Sub-Case: Attempting to dilute a solution to a concentration greater
                    than either the source solution or the diluent.
            - Both much greater and slightly greater concentrations are tested

        - Sub-Case: Attempting to dilute a solution to a concentration lower
                    than either the source solution or the diluent.
            - Both much lower and slightly lower concentrations are tested

    This unit test checks for the following success scenarios:
    - Diluent is a Substance that is not the same as the solute.
        - Standard Case - dilution of salt water to lower concentration
        - Edge Case - dilution of salt water to zero concentration
        - Edge Case - dilution of salt water to the same concentration
    - (Edge Case) Diluent is a Substance that matches the solute.
    - Diluent is a Container that does not contain any of the solute.
        - Edge Case - dilution of salt water to the same concentration
            - This was checked for both a pure Substance diluent and a Container
              diluent for 100% code coverage and to ensure that the diluent 
              Container volume was not reduced at all in this case.
    - Diluent is a Container that does contain some amount of the solute.
    - Variations for the possible units for the concentrations. 

    For each success case, the dilution was checked to ensure that it matched 
    the provided concentration/total quantity. The source solution was also 
    checked to ensure it had been reduced by the appropriate volume. Finally, if
    the diluent was a Container, it was checked to ensure it had been reduced by
    the appropriate volume.

    This unit test depends on the correctness of the following functions:
    - `Container.get_concentration()`
    - `Container.get_volume()`
    - `Container.get_quantity()`
    - `Container.create_solution()` (for 1 M and 2 M salt water fixtures)

    TODO: Include checks for proper instruction generation.
    """

    # Create an alias for `Container.create_dilution()` to save on space
    cd = Container.create_dilution

    # ==========================================================================
    # Failure Case: Invalid argument types 
    # ==========================================================================
    
    for NON_CONTAINER in [None, 1, "1", [], {}, salt, [None], [salt_water]]:
        with pytest.raises(TypeError, match="Source must be a Container\\."):
            cd(NON_CONTAINER, salt, "0.001 M", water, "10 mL")
            
    for NON_SUBSTANCE in [None, 1, "1", [], {}, salt_water, [None], [salt]]:
        with pytest.raises(TypeError, match="Solute must be a Substance\\."):
            cd(salt_water, NON_SUBSTANCE, "0.001 M", water, "10 mL")
            
    for NON_STR in [None, 1, [], {}, salt, salt_water, [None], [""], ("",)]:
        with pytest.raises(TypeError, match="Concentration must be a str\\."):
            cd(salt_water, salt, NON_STR, water, "10 mL")
            
    for INVALID_DILUENT in [None, 1, [], {}, [None], [salt], (water,)]:
        with pytest.raises(TypeError, match="Diluent must be a Substance or Container\\."):
            cd(salt_water, salt, "0.001 M", INVALID_DILUENT, "10 mL")
            
    for NON_STR in [None, 1, [], {}, salt, salt_water, [None], [""], ("",)]:
        with pytest.raises(TypeError, match="Total quantity must be a str\\."):
            cd(salt_water, salt, "0.001 M", water, NON_STR)
            
    for INVALID_NAME in [1, [], {}, salt, salt_water, [None], [""], ("",)]:
        with pytest.raises(TypeError, match="Name must be a str\\."):
            cd(salt_water, salt, "0.001 M", water, "10 mL", INVALID_NAME)
    
    for NON_STR in [None, 1, [], {}, salt, salt_water, [None], [""], ("",)]:
        with pytest.raises(TypeError, match="Maximum volume must be a str\\."):
            cd(salt_water, salt, "0.001 M", water, "10 mL", max_volume=NON_STR)
            

    # ==========================================================================
    # Failure Case: Invalid concentration value
    # ==========================================================================
    
    # Sub-Case: Concentration cannot be parsed (i.e. the call to 
    #           Unit.parse_concentration() raises a ValueError)
    for BAD_CONCEN in ['0.1', '0.1 MaM', '0.1 M M', '0.1 M M M', '0.1 L/A',
                       '0.1 mol', '0.1 g', '0.1 L', '12 kmol', '0.1 M/L',
                       'NaN M']:
        with pytest.raises(ValueError, match=r'Invalid concentration \'.*\'\.'):
            cd(salt_water, salt, BAD_CONCEN, water, "10 mL")
            
    # Sub-Case: Concentration value is nonsensical for creating a solution
    
    # Sub-Sub-Case: Concentration is not finite
    match_msg = r'Concentration must be finite\.'
    for BAD_CONCEN in ['inf M', '-inf M']:
        with pytest.raises(ValueError, match=match_msg):
            cd(salt_water, salt, BAD_CONCEN, water, "10 mL")
            
    # Sub-Sub-Case: Concentration is negative
    match_msg = r'Concentration must be non-negative\.'
    for BAD_CONCEN in ['-1 M', '-0.01 L/L']:
        with pytest.raises(ValueError, match=match_msg):
            cd(salt_water, salt, BAD_CONCEN, water, "10 mL")
            

    # ==========================================================================
    # Failure Case: Invalid total quantity value
    # ==========================================================================
    
    # Sub-Case: Total quantity cannot be parsed (i.e. the call to 
    #           Unit.parse_quantity() raises a ValueError)
    for bad_quantity in ['0.1', '0.1 Mag', '0.1 mmmol', '0.1 LLLL', '0.1 L/A', 
                       '0.0.1 g', 'NaN g', '1 M', '1 mol/L']:
        with pytest.raises(ValueError, match=r'Invalid total quantity \'.*\'\.'):
            cd(salt_water, salt, "0.001 M", water, bad_quantity)
            
    # Sub-Case: Quantity value is nonsensical for creating a solution
    
    # Sub-Sub-Case: Quantity is not finite
    match_msg = r'Total quantity must be finite\.'
    for bad_quantity in ['inf g', '-inf g']:
        with pytest.raises(ValueError, match=match_msg):
            cd(salt_water, salt, "0.001 M", water, bad_quantity)
            
    # Sub-Sub-Case: Quantity is negative
    match_msg = r'Total quantity must be positive\.'
    for bad_quantity in ['-1 mol', '-0.01 L']:
        with pytest.raises(ValueError, match=match_msg):
            cd(salt_water, salt, "0.001 M", water, bad_quantity)
    
    
    # ==========================================================================
    # Failure Case: Invalid source/solute - solute not found in source container
    # ==========================================================================
    
    match_msg = r'Source container does not contain solute \''
    with pytest.raises(ValueError, match=f"{match_msg}{dmso.name}"):
        cd(salt_water, dmso, "0.001 M", water, "10 mL")
    
    with pytest.raises(ValueError, match=f"{match_msg}{sodium_sulfate.name}"):
        cd(salt_water, sodium_sulfate, "0.001 M", water, "10 mL")
        
    
    # ==========================================================================
    # Failure Case: (Mock) Invalid concentration units
    # ==========================================================================
    
    # This failure case would ordinarily be caught by the function
    # `Unit.parse_concentration()`, but this test mocks that function to ensure
    # that incorrect units are caught correctly at a later step. Admittedly, 
    # this is peeking inside `Container.create_dilution()` more than the unit 
    # test theoretically should, but including this failure case does make the 
    # function more robust.

    # Store the true function in a variable so that it can be called later
    real_parse_concentration = Unit.parse_concentration

    # Replace calls to Unit.parse_concentration() with the mock version.
    mocker.patch.object(Unit, 'parse_concentration', mock_parse_concentration)
    
    # Check that this function correctly raises any type errors for the keywords
    # generated by the sub-call to Container._compute_solution_contents()
    match_msg = "Invalid units for concentration numerator\\."
    bad_num_concentrations = ["1 A/L", "5 mC/K", "24 hrs/day"]
    for BAD_CONCEN in bad_num_concentrations:
        with pytest.raises(ValueError, match=match_msg):
            cd(salt_water, salt, BAD_CONCEN,
                                      water, "10 mL")
    
    match_msg = "Invalid units for concentration denominator\\."
    bad_denom_concentrations = ["1 mol/A", "5 g/CK", "24 L/day"]
    for BAD_CONCEN in bad_denom_concentrations:
        with pytest.raises(ValueError, match=match_msg):
            cd(salt_water, salt, BAD_CONCEN,
                                      water, "10 mL")
    
    # Revert Container._compute_solution_contents() to its original form
    mocker.patch.object(Unit, 'parse_concentration', real_parse_concentration)
    

    # ==========================================================================
    # Failure Case: (Mock) Invalid quantity units
    # ==========================================================================
    
    # This failure case would ordinarily be caught by the function
    # `Unit.parse_quantity()`, but this test mocks that function to ensure
    # that incorrect units are caught correctly at a later step. Admittedly, 
    # this is peeking inside `Container.create_dilution()` more than the unit 
    # test theoretically should, but including this failure case does make the 
    # function more robust.

    # Store the true function in a variable so that it can be called later
    real_parse_concentration = Unit.parse_quantity

    # Replace calls to Unit.parse_quantity() with the mock version.
    mocker.patch.object(Unit, 'parse_quantity', mock_parse_quantity)
    
    # Check that this function correctly raises any type errors for the keywords
    # generated by the sub-call to Container._compute_solution_contents()
    match_msg = "Invalid quantity unit\\."
    bad_quantities = ["1 A", "5 mC", "24 hrs", "80 days"]
    for bad_qty in bad_quantities:
        with pytest.raises(ValueError, match=match_msg):
            cd(salt_water, salt, "0.001 M",
                                      water, bad_qty)
    
    # Revert Container._compute_solution_contents() to its original form
    mocker.patch.object(Unit, 'parse_quantity', real_parse_concentration)
    

    # ==========================================================================
    # Failure Case: Impossible dilution
    # ==========================================================================
    
    match_msg = r"Dilution is impossible to create\."

    # Sub-Case: Target concentration is much higher than source/diluent 
    # concentrations
    for num, denom in product(Unit.BASE_UNITS, repeat=2):
        with pytest.raises(ValueError, match=match_msg):
                cd(salt_water, salt, f"200 {num}/{denom}", water, "10 mL")

    # Sub-Case: Target concentration is slighly higher than the source/diluent
    # concentrations (slightly higher than whichever is bigger)
    # 
    # NOTE: 'salt_water' fixture has a salt concentration of '0.493356... M' 
    with pytest.raises(ValueError, match=match_msg):
            cd(salt_water, salt, "0.49336 M", water, "10 mL")
    with pytest.raises(ValueError, match=match_msg):
            cd(salt_water, salt, "0.49336 M", water_stock, "10 mL")
            
    # Sub-Case: Target concentration is much lower than source/diluent 
    # concentrations
    for num, denom in product(Unit.BASE_UNITS, repeat=2):
        with pytest.raises(ValueError, match=match_msg):
            cd(brine, salt, f"0.00001 {num}/{denom}", salt_water, "10 mL")
        
    # Sub-Case: Target concentration is slightly lower than source/diluent 
    # concentrations
    with pytest.raises(ValueError, match=match_msg):
        cd(brine, salt, "0.001 M", salt_water, "10 mL")
    with pytest.raises(ValueError, match=match_msg):
        cd(salt_water, salt, "0.001 M", brine, "10 mL")


    # ==========================================================================
    # Failure Case: Dilution requires more source than is available
    # ==========================================================================
    
    match_msg = "Not enough mixture in source\\."
    with pytest.raises(ValueError, match=match_msg):
        cd(salt_water, salt, "0.1 M", water, "2000 L")
    

    # ==========================================================================
    # Failure Case: Dilution requires more diluent than is available
    # ==========================================================================
    
    match_msg = "Not enough mixture in diluent\\."
    with pytest.raises(ValueError, match=match_msg):
        cd(salt_water, salt, "0.00001 M", water_stock, "2000 L")


    # ==========================================================================
    # Failure Case: Dilution requires more volume than the specified max volume
    # ==========================================================================
    
    match_msg = r"The total volume of the dilution exceeds the specified " \
                r"maximum volume\. Dilution volume: .*  Maximum volume: .*"
    
    # Sub-Case: Pure Substance diluent exceeds max volume
    with pytest.raises(ValueError, match=match_msg):
        cd(brine, salt, "0.01 M", water, "20 mL", max_volume="5 mL")

    # Sub-Case: Container diluent exceeds max volume
    with pytest.raises(ValueError, match=match_msg):
        cd(brine, salt, "0.1 M", water_stock, "20 mL", max_volume="5 mL")

    # Sub-Case: Source exceeds max volume
    with pytest.raises(ValueError, match=match_msg):
        cd(brine, salt, "5 M", water, "6 mL", max_volume="5 mL")

    
    # ==========================================================================
    # Failure Case: Dilution failed due to unknown transfer error
    # ==========================================================================
    
    match_msg = r"Dilution could not be created. Transfer from .* failed. " \
                r"Reason: .*"
    
    # Define a mock function that will raise an unknown error
    def _mock_transfer_error(*args, **kwargs):
        raise ValueError("This is an unknown transfer error!")

    # Store the true function in a variable so that it can be called later
    real_transfer = Container.transfer

    # Set up mocking for Container.transfer()
    mocker.patch.object(Container, 'transfer', _mock_transfer_error)

    with pytest.raises(ValueError, match=match_msg):
        cd(salt_water, salt, "0.001 M", water, "10 mL")

    # Revert Container.transfer() to its original form
    mocker.patch.object(Container, 'transfer', real_transfer)


    # ==========================================================================
    # Success Case: Create dilution with pure Substance diluent (does not
    #               overlap with solute)
    # ==========================================================================
    
    # Set starting variables
    diluted_conc = 0.01
    dilution_vol = 0.1
    dilution_name = "Diluted Salt Water"
    dilution_max_vol = "1 L" # Needs a space for proper parsing

    for diluent in [water, dmso]:
        # Create a dilution of salt water using the pure substance
        source_left, dilution = cd(salt_water, salt, f"{diluted_conc} M",
                                    diluent, f"{dilution_vol} L", 
                                    name=dilution_name,
                                    max_volume=dilution_max_vol)
        
        # Check that the dilution has the correct concentration
        assert dilution.get_concentration(salt, "M") == diluted_conc

        # Check that the dilution has the correct total amount
        assert dilution.get_volume(unit="L") == dilution_vol
        
        # Check that the name has been properly assigned
        assert dilution.name == dilution_name

        # Check that the maximum volume has been properly assigned
        amt, unit = dilution_max_vol.split(" ")
        storage_vol = Unit.convert_to_storage(float(amt), unit)
        assert dilution.max_volume == storage_vol

        # Check that the returned source container has lost the amount of solution
        # needed to create the dilution   
        src_concentration = salt_water.get_concentration(salt, "M")

        # NOTE: These calculations assume that the diluent does not contain any 
        # solute, they cannot be used for cases where the diluent is the solute or
        # contains some amount of the solute.
        salt_moles_needed = diluted_conc * dilution_vol
        expected_src_vol_used = salt_moles_needed / src_concentration
        expected_src_vol_left = salt_water.get_volume() - expected_src_vol_used

        assert source_left.get_volume("L") == pytest.approx(expected_src_vol_left)


    # ==========================================================================
    # Success Case: (Edge Case) Create dilution with pure Substance diluent that
    #               is also the solute.
    # ==========================================================================
    
    # This case would not be considered a "dilution" in practice, it would be a
    # "concentration" in the sense that the solution would become MORE 
    # concentrated in terms of the solute instead of less concentrated. This
    # could be switched to a failure case if desired, but for now it is 
    # supported behavior for this function.

    # Set starting variables
    diluted_conc = 0.5
    dilution_vol = 0.1
    dilution_name = "Concentrated Salt Water"

    # Create a dilution of salt water using pure salt
    source_left, dilution = cd(salt_water, salt, f"{diluted_conc} M",
                                    salt, f"{dilution_vol} L", 
                                    name=dilution_name)
    
    # Check that the dilution has the correct concentration
    assert dilution.get_concentration(salt, "M") == diluted_conc

    # Check that the dilution has the correct total amount
    assert dilution.get_volume(unit="L") == dilution_vol
    
    # Check that the name has been properly assigned
    assert dilution.name == dilution_name

    # Check that the returned source container has lost the amount of solution
    # needed to create the dilution   
    src_concentration = salt_water.get_concentration(salt, "M")

    # Compute the volume of salt needed for the final dilution
    salt_moles_needed = diluted_conc * dilution_vol
    salt_volume_needed = salt.convert(salt_moles_needed, 'mol', 'L')

    # Compute the amount of water that is needed for the final dilution
    water_volume_needed = dilution_vol - salt_volume_needed

    # Compute the amount of salt water needed to transfer that amount of water
    src_water_vol_fraction = salt_water.get_concentration(water, "L/L")

    # Compute the amount of salt water that is needed to transfer the water/the 
    # amount of salt water remaining after the transfer
    expected_src_vol_used = water_volume_needed / src_water_vol_fraction
    expected_src_vol_left = salt_water.get_volume() - expected_src_vol_used

    assert source_left.get_volume("L") == pytest.approx(expected_src_vol_left)

    
    # ==========================================================================
    # Success Case: (Edge Case) Create dilution with target concentration 0.
    # ==========================================================================

    # Set starting variables
    dilution_vol = 0.1
    dilution_name = "Diluted Salt Water"

    for diluent in [water, dmso]:
        # Create a dilution of salt water using the pure substance
        source_left, dilution = cd(salt_water, salt, f"0 M",
                                    diluent, f"{dilution_vol} L", 
                                    name=dilution_name)
        
        # Check that the dilution has the correct concentration
        assert dilution.get_concentration(salt, "M") == 0

        # Check that the dilution has the correct total amount
        assert dilution.get_volume(unit="L") == dilution_vol
        
        # Check that the name has been properly assigned
        assert dilution.name == dilution_name

        # Check that the returned source container has not lost any volume
        assert source_left.get_volume("L") == salt_water.get_volume("L")


    # ==========================================================================
    # Success Case: Create dilution with Container diluent (does not overlap 
    #               with solute)
    # ==========================================================================
    
    # Set starting variables
    diluted_conc = 0.01
    dilution_vol = 0.1
    dilution_name = "Diluted Salt Water"

    # Create a dilution of salt water using the pure water stock solution
    source_left, diluent_left, dilution = cd(salt_water, salt, f"{diluted_conc} M",
                                                water_stock, f"{dilution_vol} L", 
                                                name=dilution_name)
    
    # Check that the dilution has the correct concentration
    assert dilution.get_concentration(salt, "M") == diluted_conc

    # Check that the dilution has the correct total amount
    assert dilution.get_volume(unit="L") == dilution_vol
    
    # Check that the name has been properly assigned
    assert dilution.name == dilution_name

    # Check that the returned source container has lost the amount of solution
    # needed to create the dilution   
    src_concentration = salt_water.get_concentration(salt, "M")

    # NOTE: These calculations assume that the diluent does not contain any 
    # solute, they cannot be used for cases where the diluent is the solute or
    # contains some amount of the solute.
    salt_moles_needed = diluted_conc * dilution_vol
    expected_src_vol_used = salt_moles_needed / src_concentration
    expected_src_vol_left = salt_water.get_volume('L') - expected_src_vol_used

    assert source_left.get_volume("L") == pytest.approx(expected_src_vol_left)

    # Check that the returned diluent container has lost the amount of solution
    # needed to create the dilution.
    expected_solv_vol_used = dilution_vol - expected_src_vol_used
    expected_solv_vol_left = water_stock.get_volume('L') - expected_solv_vol_used

    assert diluent_left.get_volume('L') == pytest.approx(expected_solv_vol_left)


    # ==========================================================================
    # Success Case: Create dilution with Container diluent (overlaps with 
    #               solute)
    # ==========================================================================
    
    # Set starting variables
    diluted_conc = 1.5
    dilution_vol = 0.1
    dilution_name = "Concentrated Salt Water"

    # Create a dilution of 1 M salt water using 2 M salt water
    source_left, diluent_left, dilution = cd(salt_water_1M, salt, 
                                             f"{diluted_conc} M",
                                             salt_water_2M, 
                                             f"{dilution_vol} L", 
                                             name=dilution_name)
    
    # Check that the dilution has the correct concentration
    assert dilution.get_concentration(salt, "M") == diluted_conc

    # Check that the dilution has the correct total amount
    assert dilution.get_volume(unit="L") == dilution_vol
    
    # Check that the name has been properly assigned
    assert dilution.name == dilution_name

    # Check that the returned source container has lost the amount of solution
    # needed to create the dilution   
    expected_src_vol_left = salt_water_1M.get_volume('L') - dilution_vol/2
    assert source_left.get_volume('L') == expected_src_vol_left

    # Check that the returned diluent container has lost the amount of solution
    # needed to create the dilution.
    expected_solv_vol_left = salt_water_2M.get_volume('L') - dilution_vol/2
    assert diluent_left.get_volume('L') == pytest.approx(expected_solv_vol_left)


    # ==========================================================================
    # Success Case: (Edge Case) Create dilution with target concentration that
    #               matches the source concentration.
    # ==========================================================================

    # Set starting variables
    dilution_vol = 0.1
    dilution_name = "Diluted Salt Water"

    # Sub-Case: Create a dilution of salt water using the pure water substance
    source_left, dilution = cd(salt_water_1M, salt, f"1 M",
                                water, f"{dilution_vol} L", 
                                name=dilution_name)

    # Check that the dilution has the correct concentration
    assert dilution.get_concentration(salt, "M") == 1

    # Check that the dilution has the correct total amount
    assert dilution.get_volume(unit="L") == dilution_vol
    
    # Check that the name has been properly assigned
    assert dilution.name == dilution_name

    # Check that the returned source container has lost the full dilution
    # volume
    assert source_left.get_volume("L") == salt_water_1M.get_volume("L") - 0.1


    # Sub-Case: Create a dilution of salt water using the pure water stock 
    # solution
    source_left, diluent_left, dilution = cd(salt_water_1M, salt, f"1 M",
                                             water_stock, f"{dilution_vol} L", 
                                             name=dilution_name)
    
    # Check that the dilution has the correct concentration
    assert dilution.get_concentration(salt, "M") == 1

    # Check that the dilution has the correct total amount
    assert dilution.get_volume(unit="L") == dilution_vol
    
    # Check that the name has been properly assigned
    assert dilution.name == dilution_name

    # Check that the returned source container has lost the full dilution
    # volume
    assert source_left.get_volume("L") == salt_water_1M.get_volume("L") - 0.1

    # Check that the returned diluent container has not lost any volume
    assert diluent_left.get_volume("L") == water_stock.get_volume("L")


    # ==========================================================================
    # Success Case: Create dilution with various concentration/quantity units
    # ==========================================================================
    
    # NOTE: The dilution concentration is left low so that combinations like L/g
    # will still be valid concentrations (i.e not exceed the maximum value 
    # achievable for the salt water fixture).
    # 
    # Ex: The maximum value for a L/g concentration of salt with the current
    # fixture properties is ~0.0004608 L/g, as this is the concentration of pure
    # salt. The maximum concentration possible for the salt water fixture is 
    # ~1.31 x 10^-5 L/g.
    dilution_conc = 1e-5 
    dilution_qty = 0.05

    for numerator, denominator, qty_unit in product(Unit.BASE_UNITS, repeat=3):
        # Parse concentration/dilution volume from units
        conc_units = f"{numerator}/{denominator}"
        conc_str = f"{dilution_conc} {conc_units}"
        qty_str = f"{dilution_qty} {qty_unit}"

        source_left, dilution = cd(salt_water, salt, conc_str, 
                                   water, qty_str)

        # Check that the dilution has the correct concentration
        assert dilution.get_concentration(salt, conc_units) == pytest.approx(dilution_conc)

        # Check that the dilution has the correct total amount
        assert dilution.get_quantity(unit=qty_unit) == pytest.approx(dilution_qty, rel=1e-12)

def test_Container_dilute_in_place(mocker: pytest_mock.MockerFixture,
                                   water: Substance, salt: Substance,
                                   dmso: Substance, sodium_sulfate: Substance,
                                   water_stock: Container,
                                   salt_water: Container, brine: Container,
                                   salt_water_1M: Container,
                                   salt_water_2M: Container):
    """
    Unit Test for the function `Container.dilute_in_place()`

    This unit test checks the following failure scenarios:
    - Invalid argument types will result in raising a `TypeError`
    - Invalid concentration values will result in raising a `ValueError`
        - Sub-Case: Concentration cannot be parsed
        - Sub-Case: Concentration value is nonsensical for creating a solution
    - Providing a solute that is not found in the source container will result
      in raising a `ValueError`
    - Impossible dilutions will result in raising a `ValueError`
        - Sub-Case: Concentration is zero and the amount of solute in this 
                    container is non-zero.
        - Sub-Case: Concentration parameter matches the concentration of the
                    solute in the diluent.
        - Sub-Case: Concentration parameter is outside the range of the source 
                    and diluent concentrations.
    - Dilutions which require more diluent than is available will result in
      raising a `ValueError`
    - Dilutions which require more volume than the container's max volume will
      result in raising a `ValueError`
    - Dilutions which result in a transfer error when transferring diluent will 
      result in raising a `ValueError`

    This unit test checks the following success scenarios:
    - Diluent is a pure Substance
        - Standard Case: dilution of salt water to lower concentration
        - Edge Case: diluent is the same Substance as the solute
    - Diluent is a Container
        - Sub-Case: diluent does not contain any of the solute
        - Sub-Case: diluent contains a non-zero amount of the solute
    - (Edge Case) Concentration parameter matches the starting concentration
      of the source container.
        - Sub-Cases are included for both Substance and Container diluent. 
    - Variations for the possible units for the concentrations.

    In each success case, the following checks were made:
    - The dilution was checked to ensure that it matched the provided 
      concentration. 
    - If the volume of the dilution was easily calculable, it was also checked 
      to ensure that it matched the provided volume. If not, an easier check was
      used as a stand-in (e.g. checking that the amount of salt had not changed 
      for a salt water dilution with water). 
    - If the diluent was a Container, and the expected volume of diluent needed 
      was easily calculable, the diluent was checked to ensure that it had been 
      reduced by the appropriate volume.

    This unit test depends on the correctness of the following functions:
    - `Container.get_concentration()`
    - `Container.get_volume()`
    - `Container.get_moles()`
    - `Container.create_solution()` (for 1 M and 2 M salt water fixtures)

    TODO: Include checks for proper instruction generation.
    """

    # Create an alias for `Container.dilute_in_place()` to save on space
    dip = Container.dilute_in_place

    # ==========================================================================
    # Failure Case: Invalid argument types
    # ==========================================================================
    
    for NON_SUBSTANCE in [None, 1, "1", [], {}, salt_water, [None], [salt_water]]:
        with pytest.raises(TypeError, match="Solute must be a Substance\\."):
            dip(salt_water, NON_SUBSTANCE, "0.001 M", water)

    for NON_STR in [None, 1, [], {}, salt, salt_water, [None], [""], ("",)]:
        with pytest.raises(TypeError, match="Concentration must be a str\\."):
            dip(salt_water, salt, NON_STR, water)

    match_msg = "Diluent must be a Substance or a Container\\."
    for INVALID_DILUENT in [None, 1, [], {}, [None], [salt], (water,)]:
        with pytest.raises(TypeError, match=match_msg):
            dip(salt_water, salt, "0.001 M", INVALID_DILUENT)

    for INVALID_NAME in [1, [], {}, salt, salt_water, [None], [""], ("",)]:
        with pytest.raises(TypeError, match="Name must be a str\\."):
            dip(salt_water, salt, "0.001 M", water, INVALID_NAME)


    # ==========================================================================
    # Failure Case: Invalid concentration value
    # ==========================================================================
    
    # Sub-Case: Concentration cannot be parsed (i.e. the call to 
    #           Unit.parse_concentration() raises a ValueError)
    for BAD_CONCEN in ['0.1', '0.1 MaM', '0.1 M M', '0.1 M M M', '0.1 L/A',
                       '0.1 mol', '0.1 g', '0.1 L', '12 kmol', '0.1 M/L',
                       'NaN M']:
        with pytest.raises(ValueError, match=r'Invalid concentration \'.*\'\.'):
            dip(salt_water, salt, BAD_CONCEN, water)
            
    # Sub-Case: Concentration value is nonsensical for creating a solution
    
    # Sub-Sub-Case: Concentration is not finite
    match_msg = r'Concentration must be finite\.'
    for BAD_CONCEN in ['inf M', '-inf M']:
        with pytest.raises(ValueError, match=match_msg):
            dip(salt_water, salt, BAD_CONCEN, water)
            
    # Sub-Sub-Case: Concentration is negative
    match_msg = r'Concentration must be non-negative\.'
    for BAD_CONCEN in ['-1 M', '-0.01 L/L']:
        with pytest.raises(ValueError, match=match_msg):
            dip(salt_water, salt, BAD_CONCEN, water)


    # ==========================================================================
    # Failure Case: Invalid source/solute - solute not found in source container
    # ==========================================================================
    
    match_msg = r'This container does not contain solute'
    with pytest.raises(ValueError, match=f"{match_msg} {dmso.name}"):
        dip(salt_water, dmso, "0.001 M", water)
    
    with pytest.raises(ValueError, match=f"{match_msg} {sodium_sulfate.name}"):
        dip(salt_water, sodium_sulfate, "0.001 M", water)

    
    # ==========================================================================
    # Failure Case: Impossible dilution
    # ==========================================================================

    # Sub-Case: Concentration is zero and the amount of solute in the source
    #           container is non-zero.
    match_msg = r'Cannot dilute to zero concentration if the source ' \
                r'concentration is non-zero\.'
    with pytest.raises(ValueError, match=match_msg):
        dip(salt_water, salt, "0 M", water)

    # Sub-Case: Concentration parameter matches the concentration of the solute
    #           in the diluent.
    match_msg = r'The target concentration cannot match the concentration ' \
                r'of the solute in the diluent\.'
    with pytest.raises(ValueError, match=match_msg):
        dip(salt_water_2M, salt, "1 M", salt_water_1M)

    # Sub-Case: Concentration parameter lies outside the range between the 
    #           source concentration and the diluent concentration.
    match_msg = r'The target concentration for the solute must ' \
                r'lie between that of the source and the diluent.'
    with pytest.raises(ValueError, match=match_msg):
        dip(salt_water_2M, salt, "0.5 M", salt_water_1M)
    with pytest.raises(ValueError, match=match_msg):
        dip(salt_water_2M, salt, "0.999999 M", salt_water_1M)


    # ==========================================================================
    # Failure Case: Dilution requires more diluent than is available
    # ==========================================================================
    
    match_msg = "Not enough mixture in diluent\\."
    with pytest.raises(ValueError, match=match_msg):
        dip(salt_water, salt, "0.00001 M", water_stock)


    # ==========================================================================
    # Failure Case: Dilution requires more volume than the container's max 
    #               volume
    # ==========================================================================
    
    match_msg = r"The total volume of the dilution exceeds this " \
                r"container's maximum volume\. " \
                r"Dilution volume: .*  Maximum volume: .*"
    
    salt_water_with_max_vol = Container('Salt Water', '150 mL',
                                        [(salt, '0.72 mol'), (water, '100 mL')])
    
    # Sub-Case: Pure Substance diluent exceeds max volume
    with pytest.raises(ValueError, match=match_msg):
        dip(salt_water_with_max_vol, salt, "0.01 M", water)

    # Sub-Case: Container diluent exceeds max volume
    with pytest.raises(ValueError, match=match_msg):
        dip(salt_water_with_max_vol, salt, "1 M", water_stock)

    
    # ==========================================================================
    # Failure Case: Dilution failed due to unknown diluent transfer error
    # ==========================================================================
    
    match_msg = r"Dilution could not be created. Transfer of diluent failed. " \
                r"Reason: .*"
    
    # Define a mock function that will raise an unknown error
    def _mock_transfer_error(*args, **kwargs):
        raise ValueError("This is an unknown transfer error!")

    # Store the true function in a variable so that it can be called later
    real_transfer = Container.transfer

    # Set up mocking for Container.transfer()
    mocker.patch.object(Container, 'transfer', _mock_transfer_error)

    with pytest.raises(ValueError, match=match_msg):
        dip(salt_water, salt, "0.001 M", water_stock)

    # Revert Container.transfer() to its original form
    mocker.patch.object(Container, 'transfer', real_transfer)


    # ==========================================================================
    # Success Case: Pure Substance diluent
    # ==========================================================================

    # Set starting variables
    diluted_conc = 0.01
    dilution_name = "Diluted Salt Water"

    # Create a dilution of salt water using the pure Substance water fixture
    diluted_salt_water = dip(salt_water_1M, salt, f"{diluted_conc} M", water, 
                                dilution_name)
    
    # Check that the dilution has the correct concentration
    assert diluted_salt_water.get_concentration(salt, "M") == diluted_conc

    # Check that the dilution has the expected volume
    salt_moles = salt_water_1M.get_moles('mol', substance=salt)
    expected_vol = salt_moles / diluted_conc
    assert diluted_salt_water.get_volume('L') == pytest.approx(expected_vol)

    # Check that the name has been properly assigned
    assert diluted_salt_water.name == dilution_name

    # (Edge Case) Diluent is the same Substance as the solute

    # Set starting variables
    diluted_conc = 1.5
    dilution_name = "Concentrated Salt Water"

    # Create a dilution of salt water using the pure Substance water fixture
    concentrated_salt_water = dip(salt_water_1M, salt, f"{diluted_conc} M", salt, 
                                dilution_name)
    
    # Check that the dilution has the correct concentration
    assert concentrated_salt_water.get_concentration(salt, "M") == diluted_conc

    # Check that the dilution has the same amount of water as the starting 
    # container (this is being used as a proxy for checking the volume is
    # an expected amount, as the volume of the salt needed is not known)
    assert concentrated_salt_water.get_volume('L', water) == \
            salt_water_1M.get_volume('L', water)

    # Check that the name has been properly assigned
    assert concentrated_salt_water.name == dilution_name


    # ==========================================================================
    # Success Case: Container diluent (no overlap with solute)
    # ==========================================================================

    # Set starting variables
    diluted_conc = 0.75
    dilution_name = "Diluted Salt Water"

    # Create a dilution of salt water using the pure Substance water fixture
    result = dip(salt_water_1M, salt, f"{diluted_conc} M", 
                    water_stock, dilution_name)
    
    diluent_left, diluted_salt_water = result
    
    # Check that the dilution has the correct concentration
    assert diluted_salt_water.get_concentration(salt, "M") == diluted_conc

    # Check that the dilution has the expected volume
    salt_moles = salt_water_1M.get_moles('mol', substance=salt)
    expected_vol = salt_moles / diluted_conc
    assert diluted_salt_water.get_volume('L') == pytest.approx(expected_vol)

    # Check that the name has been properly assigned
    assert diluted_salt_water.name == dilution_name

    # Check that the diluent container has the expected volume remaining
    expected_water_added = expected_vol - salt_water_1M.get_volume('L')
    expected_vol_left = water_stock.get_volume('L') - expected_water_added
    assert diluent_left.get_volume('L') == pytest.approx(expected_vol_left)


    # ==========================================================================
    # Success Case: Container diluent (overlaps with solute)
    # ==========================================================================
    
    # Set starting variables
    diluted_conc = 1.5
    dilution_name = "1.5 M Salt Water"

    # Create a dilution with a salt concentration of 1.5 M from 2 M salt water 
    # using 1 M salt water as the diluent
    result = dip(salt_water_2M, salt, f"{diluted_conc} M", salt_water_1M, 
                 dilution_name)
    diluent_left, diluted_salt_water = result

    # Check that the dilution has the correct concentration
    assert diluted_salt_water.get_concentration(salt, "M") == diluted_conc

    # Check that the dilution has the expected volume
    expected_vol = 2 * salt_water_1M.get_volume('L')
    assert diluted_salt_water.get_volume('L') == expected_vol

    # Check that the name has been properly assigned
    assert diluted_salt_water.name == dilution_name

    # Check that the diluent container has the expected volume remaining
    exp_vol_left = salt_water_2M.get_volume('L') - salt_water_1M.get_volume('L')
    assert diluent_left.get_volume('L') == pytest.approx(exp_vol_left)


    # ==========================================================================
    # Success Case: (Edge Case) Create dilution with target concentration that
    #               matches the starting concentration.
    # ==========================================================================

    # Sub-Case: Solute is a pure water Substance; no name provided
    dilution = dip(salt_water_1M, salt, f"1 M", water)

    # Check that the dilution has the correct concentration
    assert dilution.get_concentration(salt, "M") == 1

    # Check that the dilution has the correct total amount
    assert dilution.get_volume(unit="L") == salt_water_1M.get_volume("L")


    # Sub-Case: Solute is a pure water Substance; name provided
    dilution_name = "Diluted Salt Water"
    dilution = dip(salt_water_1M, salt, f"1 M", water, name=dilution_name)

    # Check that the dilution has the correct concentration
    assert dilution.get_concentration(salt, "M") == 1

    # Check that the dilution has the correct total amount
    assert dilution.get_volume(unit="L") == salt_water_1M.get_volume("L")

    # Check that the name has been properly assigned
    assert dilution.name == dilution_name


    # Sub-Case: Solute is a pure water Container 
    diluent_left, dilution = dip(salt_water_1M, salt, f"1 M",
                                 water_stock, name=dilution_name)

    # Check that the dilution has the correct concentration
    assert dilution.get_concentration(salt, "M") == 1

    # Check that the dilution has the correct total amount
    assert dilution.get_volume(unit="L") == salt_water_1M.get_volume("L")
    
    # Check that the name has been properly assigned
    assert dilution.name == dilution_name

    # Check that the diluent container has not lost any volume
    assert diluent_left.get_volume("L") == water_stock.get_volume("L")


    # ==========================================================================
    # Success Case: Create dilution with various concentration/quantity units
    # ==========================================================================
    
    # NOTE: The dilution concentration is left low so that combinations like L/g
    # will still be valid concentrations (i.e not exceed the maximum value 
    # achievable for the salt water fixture).
    # 
    # Ex: The maximum value for a L/g concentration of salt with the current
    # fixture properties is ~0.0004608 L/g, as this is the concentration of pure
    # salt. The maximum concentration possible for the salt water fixture is 
    # ~1.31 x 10^-5 L/g.
    dilution_conc = 1e-5 

    for numerator, denominator in product(Unit.BASE_UNITS, repeat=2):
        # Parse concentration/dilution volume from units
        conc_units = f"{numerator}/{denominator}"
        conc_str = f"{dilution_conc} {conc_units}"

        dilution = dip(salt_water, salt, conc_str, water)

        # Check that the dilution has the correct concentration
        assert dilution.get_concentration(salt, conc_units) == pytest.approx(dilution_conc)

        # Check that the dilution has the same amount of salt as the starting
        # container (this is being used as a proxy for checking the volume is
        # an expected amount, as the volume of water needed is not known)
        assert dilution.get_moles(substance=salt) == salt_water.get_moles(substance=salt)

def test_Container_fill_to(water: Substance, salt: Substance, 
                           empty_container: Container, water_stock: Container, 
                           salt_stock: Container, salt_water: Container):
    """
    Unit Test for the function `Container.fill_to()`

    This unit test checks the following failure scenarios:
    - Invalid argument types will result in raising a `TypeError`
    - Invalid quantity values will result in raising a `ValueError`
        - Sub-Case: Quantity cannot be parsed
        - Sub-Case: Quantity is negative
        - Sub-Case: Quantity is not finite
    - Filling the container to a quantity less than the total quantity of the
      current contents will result in raising a `ValueError`
    - Filling the container to a quantity greater than the maximum volume of the
      container will result in raising a `ValueError`
    - Filling the container with a Container that contains less than the 
      remaining amount needed to reach the specified quantity will result in 
      raising a `ValueError`

    This unit test checks the following success scenarios:
    - Filling an empty Container with a pure Substance
        - Edge Case: Filling to a volume of 0
        - Edge Case: Filling with all of the fill material
    - Filling a non-empty Container with a pure Substance
        - Sub-Case: Fill material is not in the container
        - Sub-Case: Fill material is already in the container
    - Filling an empty Container with another Container
    - Filling a non-empty Container with another Container
        - Sub-Case: Fill material contents do NOT overlap with the contents of 
                    the container
        - Sub-Case: Fill material contents DO overlap with the contents of 
                    the container
    
    Each success case checks the following:
    - The container has been filled to the correct amount.
    - The substances added have the expected amounts.
    - The name of the Container has been maintained.
    - The original container object has not been modified. 
    
    In cases where the fill material is a Container, the following additional
    checks occur:
    - The returned fill material Container has been reduced by the expected 
      amount.
    - The original fill material Container has not been modified.

    This unit test depends on the correctness of the following functions:
    - `Container.get_mass()`
    - `Container.get_moles()`
    - `Container.get_volume()`
    - `Container.get_quantity()`
    - `Substance.convert()`

    TODO: Include checks for proper instruction generation.
    """

    max_vol_container = Container('Water', '100 mL')

    # ==========================================================================
    # Failure Case: Invalid argument types
    # ==========================================================================

    match_msg = "Fill material must be a Substance or a Container\\."
    for INVALID_FILLER in [None, 1, [], {}, [None], [salt], (water_stock,)]:
        with pytest.raises(TypeError, match=match_msg):
            max_vol_container.fill_to(INVALID_FILLER, "50 mL")

    match_msg = "Quantity must be a str\\."
    for INVALID_QTY in [None, 1, [], {}, [None], [salt], (water_stock,), [""]]:
        with pytest.raises(TypeError, match=match_msg):
            max_vol_container.fill_to(water, INVALID_QTY)

    
    # ==========================================================================
    # Failure Case: Quantity parameter is not valid
    # ==========================================================================

    # Sub-Case: Quantity cannot be parsed.
    match_msg = "Invalid quantity \'.*\'\\."
    for BAD_QTY in ['0.1', '0.1 L/L', '0.1 L/A', '0.1 mmmol', '0.1 C', 'nan L']:
        with pytest.raises(ValueError, match=match_msg):
            max_vol_container.fill_to(water, BAD_QTY)

    # Sub-Case: Quantity is negative
    match_msg = "Quantity must be non-negative\\."
    for BAD_QTY in ["-50 mL", "-0.0001 mol", "-132.3 g"]:
        with pytest.raises(ValueError, match=match_msg):
            max_vol_container.fill_to(water, BAD_QTY)

    # Sub-Case: Quantity is not finite
    match_msg = "Quantity must be finite\\."
    for BAD_QTY in ["-inf mL", "inf mol", "inf g"]:
        with pytest.raises(ValueError, match=match_msg):
            max_vol_container.fill_to(water, BAD_QTY)

    
    # ==========================================================================
    # Failure Case: Filling the container to a quantity less than the total
    #               quantity of the current contents
    # ==========================================================================

    match_msg = r"Quantity argument must be greater than the amount already "\
                r"in the container\. Specified quantity: .*  "\
                r"Container quantity: .*"
    
    # NOTE: This test relies on the volume of the water in the water stock
    #       fixture being more than 50 of the units specified below. At the time
    #       of writing this comment, the water stock fixture has 1 L of water.
    for unit in ["mmol", 'mL', 'g', 'mg']:
        with pytest.raises(ValueError, match=match_msg):
            water_stock.fill_to(water, f"50 {unit}")


    # ==========================================================================
    # Failure Case: Filling the container to a quantity greater than the maximum
    #               volume of the container.
    # ==========================================================================

    # Sub-Case: Filling the container with a pure Substance
    match_msg = r"Exceeded the maximum volume."
    with pytest.raises(ValueError, match=match_msg):
        max_vol_container.fill_to(water, "150 mL") 

    # Sub-Case: Filling the container with a Container
    with pytest.raises(ValueError, match=match_msg):
        max_vol_container.fill_to(water_stock, "150 mL")


    # ==========================================================================
    # Failure Case: Fill material is a Container with less than the specified 
    #               quantity
    # ==========================================================================

    match_msg = r"Not enough mixture in source container .*\. "\
                r"Only .* available, but .* needed\."
    with pytest.raises(ValueError, match=match_msg):
        empty_container.fill_to(water_stock, "1500 mL")
    with pytest.raises(ValueError, match=match_msg):
        empty_container.fill_to(water_stock, "1000.001 mL")
    

    # ==========================================================================
    # Success Case: Fill an empty container with a pure Substance
    # ==========================================================================
    
    test_amounts = ["50 mL", "1 mmol", "27 g", "51 mg", "9 mol", "626 L", 
                    "0 L", # Edge case: filling to a volume of 0
                    "1 L" # Edge case: filling with all of the fill material
                    ]
    for qty in test_amounts:
        # Fill the container with the pure Substance water
        result = empty_container.fill_to(water, qty)

        # Separate the quantity into a value-unit pair
        val, unit = qty.split(' ')
        val = float(val)

        # Check that the container has the expected quantity & volume (volume
        # check is for redundancy, as the Container tracks volume as a variable)
        assert result.get_quantity(unit) == pytest.approx(val)
        water_vol = water.convert(val, unit, 'L')
        assert result.get_volume('L') == pytest.approx(water_vol)

        # Check that the name has been maintained
        assert result.name == empty_container.name

        # Check that the original container has not been modified
        assert water not in empty_container.contents
        assert empty_container.get_volume('L') == 0

    
    # ==========================================================================
    # Success Case: Fill a non-empty container with a pure Substance
    # ==========================================================================

    # Sub-Case: Fill material is not in the container

    # NOTE: This test relies on the salt stock fixture containing exactly 1 kg 
    #       of salt. If this fixture is changed, the test will need to be 
    #       updated.
    test_amounts = ["2 L", "1 kmol", "27 kg"]
    for qty in test_amounts:
        # Fill the container with the pure Substance water
        result = salt_stock.fill_to(water, qty)

        # Separate the quantity into a value-unit pair
        val, unit = qty.split(' ')
        val = float(val)
        salt_quantity = salt.convert(1, 'kg', unit)
        expected_water = val - salt_quantity

        # Check that the container has the expected quantity & volume (volume
        # check is for redundancy, as the Container tracks volume as a variable)
        assert result.get_quantity(unit) == pytest.approx(val)
        assert result.get_mass('kg', salt) == pytest.approx(1)
        assert result.get_quantity(unit, water) == pytest.approx(expected_water)

        # Check that the name has been maintained
        assert result.name == salt_stock.name

        # Check that the original container has not been modified
        assert water not in salt_stock.contents
        assert salt_stock.get_mass('kg', salt) == 1


    # Sub-Case: Fill material is already in the container

    # NOTE: This test relies on the salt water fixture containing exactly 100 mL 
    #       of water and 50 mmol of salt. If the fixture is changed, the test 
    #       will need to be updated.
    test_amounts = ["500 mL", "1 L", "10 L"]
    for qty in test_amounts:
        # Fill the container with the pure Substance water
        result = salt_water.fill_to(water, qty)

        # Separate the quantity into a value-unit pair
        val, unit = qty.split(' ')
        val = float(val)
        salt_quantity = salt.convert(50, 'mmol', unit)
        expected_water = val - salt_quantity

        # Check that the container has the expected quantity & volume (volume
        # check is for redundancy, as the Container tracks volume as a variable)
        assert result.get_quantity(unit) == pytest.approx(val)
        assert result.get_moles('mmol', salt) == 50
        assert result.get_quantity(unit, water) == pytest.approx(expected_water)

        # Check that the name has been maintained
        assert result.name == salt_water.name

        # Check that the original container has not been modified
        assert salt_water.get_volume('mL', water) == pytest.approx(100)
        assert salt_water.get_moles('mmol', salt) == 50


    # ==========================================================================
    # Success Case: Fill an empty container with a Container
    # ==========================================================================

    test_amounts = ["50 mL", "1 mmol", "27 g", "51 mg",
                    "0 L" # Edge case: filling to a volume of 0
                    ]
    for qty in test_amounts:
        # Fill the container with water from the water stock Container
        water_left, result = empty_container.fill_to(water_stock, qty)

        # Separate the quantity into a value-unit pair
        val, unit = qty.split(' ')
        val = float(val)

        # Check that the container has the expected quantity & volume (volume
        # check is for redundancy, as the Container tracks volume as a variable)
        assert result.get_quantity(unit) == pytest.approx(val)
        water_vol = water.convert(val, unit, 'L')
        assert result.get_volume('L') == pytest.approx(water_vol)

        # Check that the name has been maintained
        assert result.name == empty_container.name

        # Check that the returned filler container has the expected volume left
        expected_vol_left = water_stock.get_volume('L') - water_vol
        assert water_left.get_volume('L') == pytest.approx(expected_vol_left)

        # Check that the original containers have not been modified
        assert water not in empty_container.contents
        assert empty_container.get_volume('L') == 0
        assert water_stock.get_volume('L') == pytest.approx(1)


    # ==========================================================================
    # Success Case: Fill a non-empty container with a Container
    # ==========================================================================

    # Sub-Case: Fill material contents do not overlap with the container

    # NOTE: This test relies on the salt stock fixture containing exactly 1 kg 
    #       of salt and the water stock fixutre containing exactly 1 L of water.
    #       If this fixture is changed, the test will need to be updated.
    test_amounts = ["1.25 kg", "1.5 kg", "1.75 kg", "2 kg"]
    for qty in test_amounts:
        # Fill the container with the pure Substance water
        water_left, result = salt_stock.fill_to(water_stock, qty)

        # Separate the quantity into a value-unit pair
        val, unit = qty.split(' ')
        val = float(val)
        salt_quantity = salt.convert(1, 'kg', unit)
        expected_water = val - salt_quantity

        # Check that the container has the expected quantity & volume (volume
        # check is for redundancy, as the Container tracks volume as a variable)
        assert result.get_quantity(unit) == pytest.approx(val)
        assert result.get_mass('kg', salt) == pytest.approx(1)
        assert result.get_quantity(unit, water) == pytest.approx(expected_water)

        # Check that the name has been maintained
        assert result.name == salt_stock.name

        # Check that the returned filler container has the expected amount left
        expected_amt_left = water_stock.get_quantity(unit) - expected_water
        assert water_left.get_quantity(unit) == pytest.approx(expected_amt_left)

        # Check that the original containers have not been modified
        assert water not in salt_stock.contents
        assert salt_stock.get_mass('kg', salt) == 1
        assert water_stock.get_volume('L') == pytest.approx(1)

    
    # Sub-Case: Fill material is already in the container

    # NOTE: This test relies on the salt water fixture containing exactly 100 mL 
    #       of water and 50 mmol of salt. If the fixture is changed, the test 
    #       will need to be updated.
    test_amounts = ["500 mL", "750 mL", "1 L"]
    for qty in test_amounts:
        # Fill the container with the pure Substance water
        water_left, result = salt_water.fill_to(water_stock, qty)

        # Separate the quantity into a value-unit pair
        val, unit = qty.split(' ')
        val = float(val)
        salt_quantity = salt.convert(50, 'mmol', unit)
        expected_water = val - salt_quantity

        # Check that the container has the expected quantity & volume (volume
        # check is for redundancy, as the Container tracks volume as a variable)
        assert result.get_quantity(unit) == pytest.approx(val)
        assert result.get_moles('mmol', salt) == 50
        assert result.get_quantity(unit, water) == pytest.approx(expected_water)

        # Check that the name has been maintained
        assert result.name == salt_water.name

        # Check that the returned filler container has the expected amount left
        transferred_water = expected_water - water.convert(100, 'mL', unit)
        expected_amt_left = water_stock.get_quantity(unit) - transferred_water
        assert water_left.get_quantity(unit) == pytest.approx(expected_amt_left)

        # Check that the original containers have not been modified
        assert salt_water.get_volume('mL', water) == pytest.approx(100)
        assert salt_water.get_moles('mmol', salt) == 50
        assert water_stock.get_volume('L') == pytest.approx(1)

def test_Container_remove(water: Substance, salt: Substance, 
                          dmso: Substance, sodium_sulfate: Substance,
                          water_stock: Container, salt_stock: Container,
                          salt_water: Container, empty_container: Container):
    """
    Unit Test for the function `Container.remove()`

    This unit test checks the following failure scenarios:
    - Invalid argument types will result in raising a `TypeError`
    - Invalid Substance types will result in raising a `ValueError`

    This unit test checks the following success scenarios:
    - Removing a single Substance from a Container
        - Sub-Case: Substance exists in the container
        - Sub-Case: Substance does not exist in the container
            - Sub-Sub-Case: Container has solid substance, removal is with liquid
            - Sub-Sub-Case: Container has liquid substance, removal is with solid
    - Removing multiple Substances from a Container
        - Sub-Case: Substances all exist in the container
        - Sub-Case: Substances all do not exist in the container
        - Sub-Case: Some Substances exist in the container, some do not
    - Removing a single Substance type from a Container
        - Sub-Case: Container contains a single substance of the removed type
        - Sub-Case: Container contains multiple substances of the removed type
        - Sub-Case: Container contains a single substance not of the removed 
                    type
        - Sub-Case: Container contains multiple substances all not of the 
                    removed type
        - Sub-Case: Container contains multiple substances, some of which are 
                    the removed type, some of which are not
    - Removing multiple Substance types from a Container
        - Sub-Case: Container is empty
        - Sub-Case: Container contains substances of one of the substance types
        - Sub-Case: Container contains substances of all substance types
    - Removing specific Substances as well as one Substance type from a 
      Container
        - Sub-Case: Removed substances/types do not cover all substances in the
                    container.
        - Sub-Case: Removed substances/types cover all substances in the 
                    container.

    For each success case, the following details are checked:
    - The contents of the resulting container has the correct number of 
      substances.
    - The substances that should have been removed are not in the container's 
      contents.
    - The substances that should have reamined are in the container's contents. 
    - The amounts of the substances that should have remained are unchanged.
    - The volume of the container has been correctly updated.
        - In cases where the resulting container is empty, the volume is 0.
        - In cases where the container is unchanged, the volume is unchanged.
        - In cases where the container is changed but not all substances are
          removed, the volume is not directly checked. Instead, correct amounts
          of the remaining substances are checked, and the volume is assumed to
          be correct if these checks pass.
    - The name of the container has been maintained.
    - The original container has not been modified.

    This unit test depends on the correctness of the following functions:
    - `Container.get_mass()`
    - `Container.get_moles()`
    - `Container.get_volume()`

    TODO: Include checks for proper instruction generation.
    """
    
    # ==========================================================================
    # Failure Case: Invalid argument types
    # ==========================================================================

    match_msg = "\'Remove Substances\' must be a Substance or an iterable set "\
                "of Substances\\."
    for INVALID_RS in [None, 1, "water", water_stock, [None], [salt_stock],
                        ("water", water), [water, water_stock]]:
          with pytest.raises(TypeError, match=match_msg):
                water_stock.remove(INVALID_RS)
    
    match_msg = "\'Remove Types\' must be a supported Substance type "\
                "or an iterable set of supported Substance types."
    for INVALID_RT in [None, "water", water, water_stock, [None], [salt],
                       [salt_stock], (water, Substance.LIQUID), 
                       [Substance.SOLID, Substance.LIQUID, water]]:
          with pytest.raises(TypeError, match=match_msg):
                water_stock.remove(remove_types=INVALID_RT)


    # ==========================================================================
    # Failure Case: Invalid Substance types
    # ==========================================================================

    match_msg = "Unsupported Substance type: .*"
    for INVALID_SUB_TYPE in [0, 12, -2, 2147483647, -2147483648]:
        with pytest.raises(ValueError, match=match_msg):
            water_stock.remove(remove_types=INVALID_SUB_TYPE)
        with pytest.raises(ValueError, match=match_msg):
            water_stock.remove(remove_types=[Substance.SOLID, INVALID_SUB_TYPE])

    
    # ==========================================================================
    # Success Case: Remove a single Substance from a Container
    # ==========================================================================

    # Sub-Case: Substance exists in the container

    # NOTE: This test relies on the salt stock fixture containing exactly 1 kg
    #       of salt. If this fixture is changed, the test will need to be 
    #       updated.
    empty = salt_stock.remove(salt)
    
    # Ensure the Substance has been removed
    assert len(empty.contents) == 0

    # Ensure the container name has been maintained
    assert empty.name == salt_stock.name

    # Ensure the volume has been correctly updated
    assert empty.volume == 0
    assert empty.get_volume('L') == 0
    
    # Ensure the original container has not been modified
    assert salt in salt_stock.contents
    assert salt_stock.get_mass('kg', salt) == 1

    # Sub-Case: Substance does not exist in the container
    
    # Sub-Sub-Case: Container has solid substance, removal is with liquid

    # NOTE: This test relies on the salt stock fixture containing exactly 1 kg
    #       of salt. If this fixture is changed, the test will need to be 
    #       updated.
    non_empty = salt_stock.remove(water)

    # Ensure the container has not been modified
    assert non_empty.contents == salt_stock.contents
    assert non_empty.volume == pytest.approx(salt_stock.volume)

    # Ensure the container name has been maintained
    assert non_empty.name == salt_stock.name

    # Ensure the original container has not been modified
    assert len(salt_stock.contents) == 1
    assert salt in salt_stock.contents
    assert salt_stock.get_mass('kg', salt) == 1

    # Sub-Sub-Case: Container has liquid substance, removal is with solid

    # NOTE: This test relies on the salt stock fixture containing exactly 1 kg
    #       of salt. If this fixture is changed, the test will need to be 
    #       updated.
    non_empty = water_stock.remove(salt)

    # Ensure the container has not been modified
    assert non_empty.contents == water_stock.contents
    assert non_empty.volume == pytest.approx(water_stock.volume)

    # Ensure the container name has been maintained
    assert non_empty.name == water_stock.name

    # Ensure the original container has not been modified
    assert len(water_stock.contents) == 1
    assert water in water_stock.contents
    assert water_stock.get_volume('L', water) == 1


    # ==========================================================================
    # Success Case: Remove multiple Substances from a Container
    # ==========================================================================

    # Sub-Case: Substances all exist in the container

    # NOTE: This test relies on the salt stock fixture containing exactly 1 kg
    #       of salt. If this fixture is changed, the test will need to be 
    #       updated.
    empty = salt_water.remove([salt, water])
    
    # Ensure the Substance has been removed
    assert len(empty.contents) == 0

    # Ensure the container name has been maintained
    assert empty.name == salt_water.name

    # Ensure the volume has been correctly updated
    assert empty.volume == 0
    assert empty.get_volume('L') == 0
    
    # Ensure the original container has not been modified
    assert salt in salt_water.contents
    assert salt_water.get_moles('mmol', salt) == 50
    assert water in salt_water.contents
    assert salt_water.get_volume('mL', water) == pytest.approx(100)

    # Sub-Case: Substances all do not exist in the container
    
    # NOTE: This test relies on the salt stock fixture containing exactly 1 kg
    #       of salt. If this fixture is changed, the test will need to be 
    #       updated.
    non_empty = salt_stock.remove([water, dmso])

    # Ensure the container has not been modified
    assert non_empty.contents == salt_stock.contents
    assert non_empty.volume == pytest.approx(salt_stock.volume)

    # Ensure the container name has been maintained
    assert non_empty.name == salt_stock.name

    # Ensure the original container has not been modified
    assert len(salt_stock.contents) == 1
    assert salt in salt_stock.contents
    assert salt_stock.get_mass('kg', salt) == 1

    # Sub-Case: Some substances exist in the container, some do not

    # NOTE: This test relies on the salt water fixture containing exactly 100 mL
    #       of water and 50 mmol of salt. If this fixture is changed, the test 
    #       will need to be updated.
    non_empty = salt_water.remove([salt, dmso])

    # Ensure the container has all the salt removed, but none of the water 
    # removed
    assert len(non_empty.contents) == 1
    assert salt not in non_empty.contents
    assert non_empty.get_moles('mmol', salt) == 0
    assert water in non_empty.contents
    assert non_empty.get_volume('mL') == pytest.approx(100)

    # Ensure the container name has been maintained
    assert non_empty.name == salt_water.name

    # Ensure the original container has not been modified
    assert salt in salt_water.contents
    assert salt_water.get_moles('mmol', salt) == 50
    assert water in salt_water.contents
    assert salt_water.get_volume('mL', water) == pytest.approx(100)


    # ==========================================================================
    # Success Case: Remove single Substance type from Container
    # ==========================================================================
    
    # Sub-Case: Container contains a single substance of the removed type
    empty = water_stock.remove(remove_types=Substance.LIQUID)

    # Ensure the Substance has been removed
    assert len(empty.contents) == 0

    # Ensure the container name has been maintained
    assert empty.name == water_stock.name

    # Ensure the volume has been correctly updated
    assert empty.volume == 0
    assert empty.get_volume('L') == 0

    # Ensure the original container has not been modified
    assert len(water_stock.contents) == 1
    assert water in water_stock.contents
    assert water_stock.get_volume('L', water) == 1

    # Sub-Case: Container contains multiple substances all of the removed type
    liquid_mixture = Container('Liquid Mixture', 
                               initial_contents=[(water, '500 mL'), 
                                                 (dmso, '500 mL')])
    empty = liquid_mixture.remove(remove_types=Substance.LIQUID)

    # Ensure the Substances have been removed
    assert len(empty.contents) == 0

    # Ensure the container name has been maintained
    assert empty.name == liquid_mixture.name

    # Ensure the volume has been correctly updated
    assert empty.volume == 0
    assert empty.get_volume('L') == 0

    # Ensure the original container has not been modified
    assert len(liquid_mixture.contents) == 2
    assert water in liquid_mixture.contents
    assert dmso in liquid_mixture.contents
    assert liquid_mixture.get_volume('mL', water) == pytest.approx(500)
    assert liquid_mixture.get_volume('mL', dmso) == pytest.approx(500)

    # Sub-Case: Container contains a single substances not of the removed type
    non_empty = water_stock.remove(remove_types=Substance.SOLID)

    # Ensure the container has not been modified
    assert non_empty.contents == water_stock.contents
    assert non_empty.volume == pytest.approx(water_stock.volume)

    # Ensure the container name has been maintained
    assert non_empty.name == water_stock.name

    # Ensure the original container has not been modified
    assert len(water_stock.contents) == 1
    assert water in water_stock.contents
    assert water_stock.get_volume('L', water) == 1

    # Sub-Case: Container contains multiple substances, none of which are the 
    # removed type
    non_empty = liquid_mixture.remove(remove_types=Substance.SOLID)

    # Ensure the container has not been modified
    assert non_empty.contents == liquid_mixture.contents
    assert non_empty.volume == pytest.approx(liquid_mixture.volume)

    # Ensure the container name has been maintained
    assert non_empty.name == liquid_mixture.name

    # Ensure the original container has not been modified
    assert len(liquid_mixture.contents) == 2
    assert water in liquid_mixture.contents
    assert dmso in liquid_mixture.contents
    assert liquid_mixture.get_volume('mL', water) == pytest.approx(500)
    assert liquid_mixture.get_volume('mL', dmso) == pytest.approx(500)

    # Sub-Case: Container contains multiple substances, some of which are the
    # removed type, some of which are not

    # Sub-Sub-Case: Removal type is liquid

    # NOTE: This test relies on the salt water fixture containing exactly 50 
    #       mmols of salt. If this fixture is changed, the test will need to be
    #       updated.
    non_empty = salt_water.remove(remove_types=[Substance.LIQUID])

    # Ensure the container has all the liquid removed, but none of the solids
    # removed
    assert len(non_empty.contents) == 1
    assert water not in non_empty.contents
    assert non_empty.get_volume('mL', water) == 0
    assert salt in non_empty.contents
    assert non_empty.get_moles('mmol', salt) == 50

    # Ensure the container name has been maintained
    assert non_empty.name == salt_water.name

    # Ensure the original container has not been modified
    assert len(salt_water.contents) == 2
    assert water in salt_water.contents
    assert salt in salt_water.contents
    assert salt_water.get_volume('mL', water) == pytest.approx(100)
    assert salt_water.get_moles('mmol', salt) == 50

    # Sub-Sub-Case: Removal type is soild

    # NOTE: This test relies on the salt water fixture containing exactly 100 mL 
    #       of water. If this fixture is changed, the test will need to be
    #       updated.
    non_empty = salt_water.remove(remove_types=[Substance.SOLID])

    # Ensure the container has all the solid removed, but none of the liquid
    # removed
    assert len(non_empty.contents) == 1
    assert salt not in non_empty.contents
    assert non_empty.get_moles('mmol', salt) == 0
    assert water in non_empty.contents
    assert non_empty.get_volume('mL', water) == pytest.approx(100)

    # Ensure the container name has been maintained
    assert non_empty.name == salt_water.name

    # Ensure the original container has not been modified
    assert len(salt_water.contents) == 2
    assert water in salt_water.contents
    assert salt in salt_water.contents
    assert salt_water.get_volume('mL', water) == pytest.approx(100)
    assert salt_water.get_moles('mmol', salt) == 50


    # ==========================================================================
    # Success Case: Remove multiple Substance types from a Container
    # ==========================================================================

    # Sub-Case: Container is empty
    empty = empty_container.remove(remove_types=[Substance.SOLID, 
                                                 Substance.LIQUID])
    
    # Ensure the container is still empty
    assert len(empty.contents) == 0
    assert empty.volume == 0
    assert empty.get_volume('L') == 0

    # Ensure the container name has been maintained
    assert empty.name == empty_container.name

    # Sub-Case: Container contains one of the substance types
    empty = water_stock.remove(remove_types=[Substance.SOLID, Substance.LIQUID])

    # Ensure the container has been emptied
    assert len(empty.contents) == 0
    assert empty.volume == 0
    assert empty.get_volume('L') == 0

    # Ensure the container name has been maintained
    assert empty.name == water_stock.name

    # Ensure the original container has not been modified
    assert len(water_stock.contents) == 1
    assert water in water_stock.contents
    assert water_stock.get_volume('L', water) == 1
    
    
    # Sub-Case: Container contains both substance types
    empty = salt_water.remove(remove_types=[Substance.SOLID, Substance.LIQUID])
    
    # Ensure the Substances have all been removed
    assert len(empty.contents) == 0
    
    # Ensure the volume has been correctly updated
    assert empty.volume == 0
    assert empty.get_volume('L') == 0

    # Ensure the container name has been maintained
    assert empty.name == salt_water.name

    # Ensure the original container has not been modified
    assert len(salt_water.contents) == 2
    assert water in salt_water.contents
    assert salt in salt_water.contents
    assert salt_water.get_volume('mL', water) == pytest.approx(100)
    assert salt_water.get_moles('mmol', salt) == 50


    # ==========================================================================
    # Success Case: Remove both specific substances and a Substance type
    # ==========================================================================
    
    solids_and_liquids = Container('Solid Liquid Mixture', 
                                   initial_contents=[(water, '100 mL'),
                                                     (dmso, '100 mL'),
                                                     (salt, '10 g'),
                                                     (sodium_sulfate, '10 g')])
    
    # Sub-Case: Remove a single Substance and a Substance type

    # Sub-Sub-Case: Remove one liquid and all solids
    non_empty = solids_and_liquids.remove(water, [Substance.SOLID])

    # Ensure the water and solids have been removed, but the DMSO remains
    assert len(non_empty.contents) == 1
    assert water not in non_empty.contents
    assert salt not in non_empty.contents
    assert sodium_sulfate not in non_empty.contents
    assert dmso in non_empty.contents
    assert non_empty.get_volume('mL', dmso) == pytest.approx(100)

    # Ensure the container name has been maintained
    assert non_empty.name == solids_and_liquids.name

    # Ensure the original container has not been modified
    assert len(solids_and_liquids.contents) == 4
    assert water in solids_and_liquids.contents
    assert dmso in solids_and_liquids.contents
    assert salt in solids_and_liquids.contents
    assert sodium_sulfate in solids_and_liquids.contents
    assert solids_and_liquids.get_volume('mL', water) == pytest.approx(100)
    assert solids_and_liquids.get_volume('mL', dmso) == pytest.approx(100)
    assert solids_and_liquids.get_mass('g', salt) == pytest.approx(10)
    assert solids_and_liquids.get_mass('g', sodium_sulfate) == pytest.approx(10)

    # Sub-Sub-Case: Remove one solid and all liquids
    non_empty = solids_and_liquids.remove(salt, [Substance.LIQUID])

    # Ensure the salt and liquids have been removed, but the sodium sulfate
    # remains
    assert len(non_empty.contents) == 1
    assert salt not in non_empty.contents
    assert water not in non_empty.contents
    assert dmso not in non_empty.contents
    assert sodium_sulfate in non_empty.contents
    assert non_empty.get_mass('g', sodium_sulfate) == pytest.approx(10)

    # Ensure the container name has been maintained
    assert non_empty.name == solids_and_liquids.name

    # Ensure the original container has not been modified
    assert len(solids_and_liquids.contents) == 4
    assert water in solids_and_liquids.contents
    assert dmso in solids_and_liquids.contents
    assert salt in solids_and_liquids.contents
    assert sodium_sulfate in solids_and_liquids.contents
    assert solids_and_liquids.get_volume('mL', water) == pytest.approx(100)
    assert solids_and_liquids.get_volume('mL', dmso) == pytest.approx(100)
    assert solids_and_liquids.get_mass('g', salt) == pytest.approx(10)
    assert solids_and_liquids.get_mass('g', sodium_sulfate) == pytest.approx(10)

    # Sub-Case: Remove multiple Substances and a Substance type

    # Sub-Sub-Case: Remove both liquids and all solids
    empty = solids_and_liquids.remove([water, dmso], [Substance.SOLID])

    # Ensure all substance have been removed
    assert len(empty.contents) == 0

    # Ensure the volume has been correctly updated
    assert empty.volume == 0
    assert empty.get_volume('L') == 0

    # Ensure the container name has been maintained
    assert empty.name == solids_and_liquids.name

    # Ensure the original container has not been modified
    assert len(solids_and_liquids.contents) == 4
    assert water in solids_and_liquids.contents
    assert dmso in solids_and_liquids.contents
    assert salt in solids_and_liquids.contents
    assert sodium_sulfate in solids_and_liquids.contents
    assert solids_and_liquids.get_volume('mL', water) == pytest.approx(100)
    assert solids_and_liquids.get_volume('mL', dmso) == pytest.approx(100)
    assert solids_and_liquids.get_mass('g', salt) == pytest.approx(10)
    assert solids_and_liquids.get_mass('g', sodium_sulfate) == pytest.approx(10)

    # Sub-Sub-Case: Remove both solids and all liquids
    empty = solids_and_liquids.remove([salt, sodium_sulfate], 
                                      [Substance.LIQUID])
    
    # Ensure all substance have been removed
    assert len(empty.contents) == 0

    # Ensure the volume has been correctly updated
    assert empty.volume == 0
    assert empty.get_volume('L') == 0

    # Ensure the container name has been maintained
    assert empty.name == solids_and_liquids.name

    # Ensure the original container has not been modified
    assert len(solids_and_liquids.contents) == 4
    assert water in solids_and_liquids.contents
    assert dmso in solids_and_liquids.contents
    assert salt in solids_and_liquids.contents
    assert sodium_sulfate in solids_and_liquids.contents
    assert solids_and_liquids.get_volume('mL', water) == pytest.approx(100)
    assert solids_and_liquids.get_volume('mL', dmso) == pytest.approx(100)
    assert solids_and_liquids.get_mass('g', salt) == pytest.approx(10)
    assert solids_and_liquids.get_mass('g', sodium_sulfate) == pytest.approx(10)
