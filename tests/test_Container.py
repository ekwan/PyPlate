import pytest
from itertools import product
from copy import deepcopy

from pyplate import Container, Substance, Unit, config

from .unit_test_constants import epsilon, \
                            test_names, \
                            test_whitespace_patterns, \
                            test_non_parseable_quantities, \
                            test_invalid_values, \
                            test_base_units, \
                            test_prefixes, \
                            test_units, \
                            test_invalid_units, \
                            test_volume_units, \
                            test_positive_volumes, \
                            test_negative_volumes, \
                            test_zero_volumes, \
                            test_quantities, \
                            test_positive_quantities, \
                            test_negative_quantities, \
                            test_zero_quantities

from .common_mock_functions import mock_parse_quantity


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

    with pytest.raises(TypeError, match="Name must be a str"):
        Container(1)
    with pytest.raises(TypeError, match="Name must be a str"):
        Container(None)
    with pytest.raises(TypeError, match="Name must be a str"):
        Container([])
    
    with pytest.raises(TypeError, match='Maximum volume must be a str'):
        Container('container', 1)
    with pytest.raises(TypeError, match='Maximum volume must be a str'):
        Container('container', None)
    with pytest.raises(TypeError, match='Maximum volume must be a str'):
        Container('container', [])


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
    with pytest.raises(ValueError, match='Exceeded maximum volume'):
        container._self_add(water, '10 mL')
    with pytest.raises(ValueError, match='Exceeded maximum volume'):
        container._self_add(dmso, '20 mL')
    with pytest.raises(ValueError, match='Exceeded maximum volume'):
        container._self_add(salt, '5.01 mL')
    with pytest.raises(ValueError, match='Exceeded maximum volume'):
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
                             empty_container, empty_plate):
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
    Unit.parse_quantity = mock_parse_quantity

    for value in ['0.5', '10', '4', '12', '200000', '7.42']:
        for unit in ['pestles', 'C', 'units', 'quantities']:
            quantity = value + ' ' + unit
            with pytest.raises(ValueError, 
                               match=f'Invalid quantity unit \'{unit}\'\\.'):
                container2._transfer(container1, quantity)
    
    # Revert Unit.parse_quantity() to the original version
    Unit.parse_quantity = real_parse_quantity


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
                        match='Not enough mixture left in source container' + 
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
        with pytest.raises(ValueError, match='Exceeded maximum volume'):
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

def test_Container_transfer(water_stock, salt_water, empty_plate, water_plate, mocker):
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

def test_create_solution(water, dmso, 
                        salt, triethylamine, sodium_sulfate):
    """
    Unit Test for the function `Container.create_solution()`

    This unit test checks the following failure scenarios:
    - Invalid argument types will result in raising a `TypeError`
    - Invalid argument values will result in raising a `ValueError`.

    This unit test checks the following success scenarios:
    - 
    """
    
    # ==========================================================================
    # Failure Case: Invalid argument types (non-keyword)
    # ==========================================================================

    with pytest.raises(TypeError, match='Solute\\(s\\) must be a Substance\\.'):
        Container.create_solution('salt', water, concentration='0.5 M', total_quantity='100 mL')

    with pytest.raises(TypeError, match='Name must be a str\\.'):
        Container.create_solution(salt, water, 1, conventration='0.5 M', total_quantity='100 mL')
    with pytest.raises(TypeError, match='Name must be a str\\.'):
        Container.create_solution(salt, water, [], conventration='0.5 M', total_quantity='100 mL')
    with pytest.raises(TypeError, match='Name must be a str\\.'):
        Container.create_solution(salt, water, False, conventration='0.5 M', total_quantity='100 mL')
    
    with pytest.raises(TypeError, match='Solvent must be a Substance or a Container\\.'):
        Container.create_solution(salt, 'water', concentration='0.5 M', total_quantity='100 mL')


    # ==========================================================================
    # Failure Case: Invalid argument types (keyword)
    # ==========================================================================
    
    # Set up mock function for Container._compute_solution_contents()
    real_compute_solution_contents = Container._compute_solution_contents

    def mock_compute_type_error(solute, solvent, **kwargs):
        raise TypeError("THIS IS A TEST TYPE ERROR!")
    
    Container._compute_solution_contents = mock_compute_type_error
    
    # Check that this function correctly raises any type errors for the keywords
    # generated by the sub-call to Container._compute_solution_contents()
    with pytest.raises(TypeError, match="THIS IS A TEST TYPE ERROR!"):
        Container.create_solution(salt, water)

    # Revert Container.compute_solution_contents() to the true function.
    Container._compute_solution_contents = real_compute_solution_contents


    # ==========================================================================
    # Failure Case: Invalid argument values (non-keyword and keyword)
    # ==========================================================================

    # Set up mock function for Container._compute_solution_contents()
    real_compute_solution_contents = Container._compute_solution_contents

    def mock_compute_value_error(solute, solvent, **kwargs):
        raise ValueError("THIS IS A TEST VALUE ERROR!")
    
    Container._compute_solution_contents = mock_compute_value_error

    # Check that this function correctly raises any type errors for the keywords
    # generated by the sub-call to Container._compute_solution_contents()
    with pytest.raises(ValueError, match="THIS IS A TEST VALUE ERROR!"):
        Container.create_solution(salt, water)

    # Revert Container.compute_solution_contents() to the true function.
    Container._compute_solution_contents = real_compute_solution_contents
    
    """
    Create a solution using each a quantity of each solvent and solute in each unit.
    Try "0.001 numerator/denominator" and "0.01 numerator/10 denominator"
    Ensure the correct amount of solvent, solute, and total solution is applied.
    """
    solvents = [water, dmso]
    solutes = [salt, triethylamine, sodium_sulfate]
    units = ['g', 'mol', 'mL']
    for numerator, denominator, quantity_unit in product(units, repeat=3):
        for solute in solutes:
            for solvent in solvents:
                if numerator == 'mL' and solute.is_solid() and solute.density == float('inf'):
                    continue
                con = Container.create_solution(solute, solvent, concentration=f"0.001 {numerator}/{denominator}",
                                                total_quantity=f"10 {quantity_unit}")
                assert all(value > 0 for value in con.contents.values())
                total = sum(substance.convert_quantity(f"{value} {config.moles_storage_unit}", quantity_unit) 
                                for substance, value in con.contents.items())
                assert abs(total - 10) < epsilon, f"Making 10 {quantity_unit} of a 0.001 {numerator}/{denominator}" \
                                                  f" solution of {solute} and {solvent} failed."
                conc = con.get_concentration(solute, f"{numerator}/{denominator}")
                assert abs(conc - 0.001) < epsilon, f"{solute} and {solvent} failed to create a 0.001 {numerator}/{denominator}"

                con = Container.create_solution(solute, solvent, concentration=f"0.01 {numerator}/10 {denominator}",
                                                total_quantity=f"10 {quantity_unit}")
                total = 0
                for substance, value in con.contents.items():
                    total += substance.convert(value, config.moles_storage_unit, quantity_unit)
                assert abs(total - 10) < epsilon
                conc = con.get_concentration(solute, f"{numerator}/{denominator}")
                assert abs(conc - 0.01/10) < epsilon






# def test_get_concentration(water, salt, dmso):
#     """

#     Tests get_concentration method of Container.

#     It checks the following scenarios:
#     - The argument types are correctly validated.
#     - The method returns the correct concentration of the substance in the container.
#     - The method raises a ValueError if the substance is not in the container.

#     """

#     # Argument types checked
#     container = Container('container', '10 mL')
#     with pytest.raises(TypeError, match='Solute must be a Substance'):
#         container.get_concentration('water')
#     with pytest.raises(TypeError, match='Units must be a str'):
#         container.get_concentration(water, 1)

#     # Check if the method returns the correct concentration of the substance in the container
#     for value in [0.1, 0.5, 1.0]:
#         stock = Container.create_solution(salt, water, concentration=f"{value} M", total_quantity='100 mL')
#         assert stock.get_concentration(salt) == pytest.approx(value, abs=1e-3)

#     ratio = stock.contents[salt] / sum(stock.contents.values())
#     assert pytest.approx(ratio, abs=1e-3) == stock.get_concentration(salt, 'mol/mol')
#     # Try to get the concentration of a substance that is not in the container
#     assert stock.get_concentration(dmso) == 0


# def test_create_solution_from(water, salt):
#     # Create a stock solution of 1 M salt water
#     stock = Container.create_solution(salt, water, concentration='1 M', total_quantity='100 mL')

#     # Create a solution of 0.5 M salt water from the stock solution
#     stock, solution = Container.create_solution_from(stock, salt,'0.5 M', water, '50 mL')

#     # Should contain 25 mmol of salt and have a total volume of 50 mL
#     assert pytest.approx(salt.convert_quantity('25 mmol', config.moles_storage_unit)) == solution.contents[salt]
#     assert pytest.approx(water.convert_quantity('50 mL', config.volume_storage_unit)) == solution.volume
#     assert pytest.approx(Unit.convert_from_storage(solution.volume, 'mL')) == 50.0

#     # stock should have a volume of 75 mL and 75 mmol of salt
#     # Try to create a solution with more volume than the source container holds
#     with pytest.raises(ValueError, match='Not enough mixture left in source container'):
#         Container.create_solution_from(stock, salt, '1 M', water, '100 mL')

# def test_create_solution(water, salt, sodium_sulfate):

#     # create solution with just one solute
#     simple_solution = Container.create_solution(salt, water, concentration='1 M', total_quantity='100 mL')

#     water_container = Container('water', initial_contents=[(water, '100 mL')])

#     # create solution with multiple solutes
#     conc_quant_solution = Container.create_solution([salt, sodium_sulfate], water,
#                                                     concentration=['1 M', '1 M'],
#                                                     quantity=['5.84428 g', '14.204 g'])
#     conc_total_quant_solution = Container.create_solution([salt, sodium_sulfate], water,
#                                                           concentration=['1 M', '1 M'],
#                                                           total_quantity='100 mL')

#     qaunt_total_quant_solution = Container.create_solution([salt, sodium_sulfate], water,
#                                                            quantity=['5.84428 g', '14.204 g'],
#                                                            total_quantity='100 mL')

#     # create solvent container
#     water_container = Container('water', initial_contents=[(water, '100 mL')])

#     # create solvent container with solute in it
#     invalid_solvent_container = Container.create_solution(salt, water, concentration='1 M', total_quantity='100 mL')


#     ## verify simple solution
#     # verify solute amount
#     assert (pytest.approx(salt.convert(100, 'mmol', config.moles_storage_unit)) ==
#             simple_solution.contents[salt])
#     # verify concentration
#     assert simple_solution.get_concentration(salt) == pytest.approx(1)
#     # verify total volume
#     assert (pytest.approx(water.convert(100, 'mL', config.volume_storage_unit)) ==
#             simple_solution.volume)

#     ## verify conc_quant_solution
#     # verify solute amounts
#     assert (pytest.approx(salt.convert(5.84428, 'g', config.moles_storage_unit)) ==
#             conc_quant_solution.contents[salt])
#     assert (pytest.approx(sodium_sulfate.convert(14.204, 'g', config.moles_storage_unit)) ==
#             conc_quant_solution.contents[sodium_sulfate])
#     # verify concentration
#     assert conc_quant_solution.get_concentration(salt) == pytest.approx(1)
#     assert conc_quant_solution.get_concentration(sodium_sulfate) == pytest.approx(1)
#     # verify total volume
#     assert (pytest.approx(water.convert(100, 'mL', config.volume_storage_unit)) ==
#             conc_quant_solution.volume)

#     ## verify conc_total_quant_solution
#     # verify solute amounts
#     assert (pytest.approx(salt.convert(5.84428, 'g', config.moles_storage_unit)) ==
#             conc_total_quant_solution.contents[salt])
#     assert (pytest.approx(sodium_sulfate.convert(14.204, 'g', config.moles_storage_unit)) ==
#             conc_total_quant_solution.contents[sodium_sulfate])
#     # verify concentration
#     assert conc_total_quant_solution.get_concentration(salt) == pytest.approx(1)
#     assert conc_total_quant_solution.get_concentration(sodium_sulfate) == pytest.approx(1)
#     # verify total volume
#     assert (pytest.approx(water.convert(100, 'mL', config.volume_storage_unit)) ==
#             conc_total_quant_solution.volume)

#     ## verify qaunt_total_quant_solution
#     # verify solute amounts
#     assert (pytest.approx(salt.convert(5.84428, 'g', config.moles_storage_unit)) ==
#             qaunt_total_quant_solution.contents[salt])
#     assert (pytest.approx(sodium_sulfate.convert(14.204, 'g', config.moles_storage_unit)) ==
#             qaunt_total_quant_solution.contents[sodium_sulfate])
#     # verify concentration
#     assert qaunt_total_quant_solution.get_concentration(salt) == pytest.approx(1)
#     assert qaunt_total_quant_solution.get_concentration(sodium_sulfate) == pytest.approx(1)
#     # verify total volume
#     assert (pytest.approx(water.convert(100, 'mL', config.volume_storage_unit)) ==
#             qaunt_total_quant_solution.volume)

#     with pytest.raises(ValueError, match="Solution is impossible to create."):
#         # create solution with solute in solvent container
#         invalid_container_solution = Container.create_solution([salt, sodium_sulfate], invalid_solvent_container,
#                                                                concentration='1 M', quantity=['1 g', '0.5 g'])

#     with pytest.raises(ValueError, match="Solution is impossible to create."):
#         # invalid quantity of solute
#         container_solution = Container.create_solution([salt, sodium_sulfate], water_container,
#                                                        concentration=['1 M', '1 M'],
#                                                        quantity=['1 g', '0.5 g'])


    # TODO: Move this to the _transfer() unit test
    #
    # initial_hashes = hash(water_stock), hash(salt_water)
    # # water_stock is 10 mL, salt_water is 100 mL and 50 mmol
    # salt_water_volume = Unit.convert_from_storage(salt_water.volume, 'mL')
    # container1, container2 = Container.transfer(salt_water, water_stock, f"{salt_water_volume*0.1} mL")
    # # 10 mL of water and 5 mol of salt should have been transferred
    # assert container1.volume == water.convert_quantity('90 mL', config.volume_storage_unit) \
    #        + salt.convert_quantity('45 mmol', config.volume_storage_unit)
    # assert container1.contents[water] == water.convert_quantity('90 mL', config.moles_storage_unit)
    # assert container1.contents[salt] == salt.convert_quantity('45 mmol', config.moles_storage_unit)
    # assert container2.volume == water.convert_quantity('20 mL', config.volume_storage_unit)\
    #        + salt.convert_quantity('5 mmol', config.volume_storage_unit)
    # assert salt in container2.contents and container2.contents[salt] == \
    #        salt.convert_quantity('5 mmol', config.moles_storage_unit)
    # assert container2.contents[water] == pytest.approx(water.convert_quantity('20 mL', config.moles_storage_unit))

    # # Original containers should be unchanged.
    # assert initial_hashes == (hash(water_stock), hash(salt_water))

    # salt_stock = Container('salt stock', initial_contents=[(salt, '10 g')])
    # container1, container2 = Container.transfer(salt_stock, salt_water, '1 g')
    # assert container2.contents[salt] == \
    #        pytest.approx(salt_water.contents[salt] + salt.convert_quantity('1 g', config.moles_storage_unit))

