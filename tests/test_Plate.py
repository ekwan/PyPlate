import pytest

from itertools import product
from typing import Iterable

import numpy
from pyplate import config, Container, Plate, Substance, Unit

from .unit_test_constants import epsilon, \
                            test_names, \
                            test_whitespace_patterns, \
                            test_non_parseable_quantities, \
                            test_invalid_values, \
                            test_invalid_units, \
                            test_volume_units, \
                            test_negative_volumes, \
                            test_zero_volumes, \
                            test_positive_volumes
                            

def test_Plate___init__():
    """
    Unit Test for `Plate.__init__()`.

    This unit test checks the following scenarios:

    Failure Cases:
    - Invalid argument types result in raising a `TypeError`
    - Invalid argument values result in raising a `ValueError` with an 
      appropriate message.

    Success Cases:
    - Plate is successfully created with:
      1. Only 'name' and 'max_volume_per_well' provided.
      2. 'name', 'max_volume_per_well', and 'make' provided.
      3. 'name', 'max_volume_per_well', and 'rows' provided.
      4. 'name', 'max_volume_per_well', and 'columns' provided.
      5. All arguments ('name', 'max_volume_per_well', 'make', 'rows', 'columns') provided.

    - For all success cases, the following attributes are verified:
      1. 'name' matches the constructor argument.
      2. 'max_volume_per_well' matches the parsed and converted value.
      3. 'make' matches the constructor argument or default value.
      4. 'n_rows' and 'n_columns' match the constructor arguments or defaults.
      5. 'row_names' and 'column_names' match the constructor arguments if provided.
      6. 'wells' array shape matches the specified rows and columns.
      7. The first well's name matches the expected format.
    """

    # ==========================================================================
    # Failure Case: Invalid Argument Types
    # ==========================================================================
    
    non_str = [None, False, 1, 1.0, [], {}, ["10 mL"], ("10 L",)]
    for name in non_str:
        with pytest.raises(TypeError, match='Name must be a str.'):
            Plate(name, '10 uL')

    for volume in non_str:
        with pytest.raises(TypeError, match='Maximum volume must be a str'):
            Plate('plate', volume)

    for make in non_str:
        with pytest.raises(TypeError, match='Make must be a str'):
            Plate('plate', '10 uL', make=make)

    invalid_rows_cols = [None, False, "1", "Row A", [1, 2, 3], ("My Row", 2), 
                         (1, "My Second Row", "My Third Row")]
    for bad_row in invalid_rows_cols:
        with pytest.raises(TypeError, match='Rows must be an integer or an ' \
                                            'iterable set of row names.'):
            Plate('plate', '10 uL', rows=bad_row)

    for bad_col in invalid_rows_cols:
        with pytest.raises(TypeError, match='Columns must be an integer or an '\
                                            'iterable set of column names.'):
            Plate('plate', '10 uL', columns=bad_col)


    # ==========================================================================
    # Failure Case: Empty name
    # ==========================================================================

    with pytest.raises(ValueError, match='Name must not be empty.'):
        Plate('', '50 mL')


    # ==========================================================================
    # Failure Case: Names with only whitespace
    # ==========================================================================

    for test_name in test_whitespace_patterns:
        merged_test_name = test_name.replace('e', '')
        if merged_test_name != '':
            error_msg = "Name must contain non-whitespace characters."
            with pytest.raises(ValueError, match=error_msg):
                Plate(merged_test_name, '50 uL')


    # ==========================================================================
    # Failure Case: Maximum volume per well is not formatted as 'value unit'
    # ==========================================================================
    # 
    # NOTE: This is really a failure case for Unit.parse_quantity(), not 
    # for constructing Plates. However, it is still worth checking here in case
    # the call to Unit.parse_quantity() is not correctly implemented in the 
    # constructor for Plate. The error type and message are not checked here, as
    # that would further couple this test to the implementation details of 
    # Unit.parse_quantity(). 

    for test_quantity in test_non_parseable_quantities:
        for pattern in test_whitespace_patterns:
            merged_test_quantity = pattern.replace('e', test_quantity)
            with pytest.raises(Exception):
                Plate('plate',
                      max_volume_per_well=merged_test_quantity)
                

    # ==========================================================================
    # Failure Case: Maximum volume per well 'value' cannot be parsed as a float
    # ==========================================================================
    #
    # NOTE: This is really a failure case for Unit.parse_quantity(), not for 
    # constructing Plates. However, it is still worth checking here in case the
    # call to Unit.parse_quantity() is not correctly implemented in the 
    # constructor for Plate. The error type and message are not checked here, as
    # that would further couple this test to the implementation details of 
    # Unit.parse_quantity(). 

    for test_value in test_invalid_values:
        for unit in test_volume_units:
            test_volume = test_value + ' ' + unit
            for pattern in test_whitespace_patterns:
                merged_test_value = pattern.replace('e', test_volume)
                with pytest.raises(Exception):
                    Plate('plate', merged_test_value)


    # ==========================================================================
    # Failure Case: Maximum volume 'unit' is not a valid unit
    # ==========================================================================
    #
    # NOTE: This is really a failure case for Unit.parse_quantity(), not for 
    # constructing Plates. However, it is still worth checking here in case the
    # call to Unit.parse_quantity() is not correctly implemented in the 
    # constructor for Plate. The error type and message are not checked here, as
    # that would further couple this test to the implementation details of 
    # Unit.parse_quantity(). 

    for unit in test_invalid_units:
        for pattern in test_whitespace_patterns:
            merged_test_value = pattern.replace('e', '10 ' + unit)
            with pytest.raises(Exception):
                Plate('plate', merged_test_value)


    # ==========================================================================
    # Failure Case: Maximum volume per well 'unit' does not represent volume
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
            # NOTE: The parentheses and periods are special characters for 
            # regular expression patterns, so they need to be escaped.
            with pytest.raises(
                ValueError, 
                match="Maximum volume per well must have volume units "
                      "\\(e\\.g\\. L, mL, uL, etc\\.\\)\\."):
                
                Plate('plate', pattern.replace('e','100 ' + test_unit))


    # ==========================================================================
    # Failure Case: Maximum volume per well is non-positive
    # ==========================================================================
    
    for test_volume in test_negative_volumes:
        for pattern in test_whitespace_patterns:
            with pytest.raises(
                ValueError, 
                match="Maximum volume per well must be positive\\."):
                
                Plate('plate', pattern.replace('e',test_volume))

    for test_volume in test_zero_volumes:
        for pattern in test_whitespace_patterns:
            with pytest.raises(
                ValueError, 
                match="Maximum volume per well must be positive\\."):
                
                Plate('palte', pattern.replace('e',test_volume))


    # ==========================================================================
    # Failure Case: Maximum volume per well is NaN
    # ==========================================================================
    
    for pattern in test_whitespace_patterns:
        with pytest.raises(
            ValueError, 
            match="'NaN' values are forbidden for quantities\\."):
            
            Plate('plate', pattern.replace('e','nan L'))


    # ==========================================================================
    # Failure Case: Empty make
    # ==========================================================================
    
    with pytest.raises(ValueError, match='Make must not be empty.'):
        Plate('Bad Make', '50 mL', make='')


    # ==========================================================================
    # Failure Case: Makes with only whitespace
    # ==========================================================================

    for test_make in test_whitespace_patterns:
        merged_test_make = test_make.replace('e', '')
        if merged_test_make != '':
            error_msg = "Make must contain non-whitespace characters."
            with pytest.raises(ValueError, match=error_msg):
                Plate("Whitespace Make", '50 uL', make=merged_test_make)

    
    # ==========================================================================
    # Failure Case: Invalid row/column count
    # ==========================================================================
    
    for row in [0, -1, -1000]:
        with pytest.raises(ValueError, 
                           match='Number of rows must be positive\\.'):
            Plate("Low Row Plate", '50 mL', rows=row)

    for col in [0, -1, -1000]:
        with pytest.raises(ValueError, 
                           match='Number of columns must be positive\\.'):
            Plate("Low Column Plate", '50 mL', columns=col)


    # ==========================================================================
    # Failure Case: Empty row/column list
    # ==========================================================================
    
    with pytest.raises(ValueError, 
                        match='Number of rows must be positive\\.'):
            Plate("Empty Row Plate", '50 mL', rows=[])

    with pytest.raises(ValueError, 
                        match='Number of columns must be positive\\.'):
            Plate("Empty Column Plate", '50 mL', columns=[])


    # These names will be used for the next few failure cases
    valid_row_col_names = [
        "Valid Row/Col 1", 
        "Valid Row/Col 2", 
        "Valid Row/Col 3"
    ]

    # ==========================================================================
    # Failure Case: Empty row/column names
    # ==========================================================================
    
    # Test different positions to ensure the empty name is recognized regardless
    # of where it is in the list
    for i in range(len(valid_row_col_names) + 1):
        with pytest.raises(ValueError, 
                            match='Row names must not be empty\\.'):
            row_names = valid_row_col_names.copy()
            row_names.insert(i, "")
            Plate("Empty Row Plate", '50 mL', rows=row_names)

    # Test different positions to ensure the empty name is recognized regardless
    # of where it is in the list
    for i in range(len(valid_row_col_names) + 1):
        with pytest.raises(ValueError, 
                            match='Column names must not be empty\\.'):
            col_names = valid_row_col_names.copy()
            col_names.insert(i, "")
            Plate("Empty Column Plate", '50 mL', columns=col_names)


    # ==========================================================================
    # Failure Case: Row/column names with only whitespace
    # ==========================================================================
    
    # Test different positions to ensure the whitespace name is recognized 
    # regardless of where it is in the list
    for i in range(len(valid_row_col_names) + 1):
        with pytest.raises(
            ValueError, 
            match='Row names must contain non-whitespace characters\\.'):
            
            row_names = valid_row_col_names.copy()
            row_names.insert(i, " \n\t")
            Plate("Whitespace Row Plate", '50 mL', rows=row_names)

    # Test different positions to ensure the whitespace name is recognized 
    # regardless of where it is in the list
    for i in range(len(valid_row_col_names) + 1):
        with pytest.raises(
            ValueError, 
            match='Column names must contain non-whitespace characters\\.'):
            
            col_names = valid_row_col_names.copy()
            col_names.insert(i, " \n\t")
            Plate("Whitespace Column Plate", '50 mL', columns=col_names)


    # ==========================================================================
    # Failure Case: Duplicate row/column names
    # ==========================================================================
    
    # Test different positions to ensure the duplicate names are recognized 
    # regardless of where they are in the list
    n = len(valid_row_col_names)
    for i, j in product(range(n), range(n + 1)):
        with pytest.raises(
            ValueError, 
            match='Row names must not be duplicated\\.'):
            
            row_names = valid_row_col_names.copy()
            row_names.insert(i, "Duplicate Name")
            row_names.insert(j, "Duplicate Name")
            Plate("Duplicate Row Plate", '50 mL', rows=row_names)

    # Test different positions to ensure the duplicate names are recognized 
    # regardless of where they are in the list
    for i, j in product(range(n), range(n + 1)):
        with pytest.raises(
            ValueError, 
            match='Column names must not be duplicated\\.'):
            
            col_names = valid_row_col_names.copy()
            col_names.insert(i, "Duplicate Name")
            col_names.insert(j, "Duplicate Name")
            Plate("Duplicate Column Plate", '50 mL', columns=col_names)

    
    # ==========================================================================
    # Success Case: Only name and maximum volume per well provided
    # ==========================================================================
    
    # Pre-compute parsed quantities to save time
    parsed_test_volumes = map(Unit.parse_quantity, test_positive_volumes)

    # Test various name/volume combinations to ensure robust behavior
    for test_name in test_names:
        for test_volume, (test_value, test_unit) in zip(test_positive_volumes,
                                                        parsed_test_volumes):
            test_plate = Plate(test_name, test_volume)

            # Check for correct name, max_volume_per_well, make, n_rows, n_columns,
            # and number of wells in the constructed Plate object.
            assert test_plate.name == test_name, \
                "Plate 'name' attribute does not match 'name' constructor argument."
            assert test_plate.max_volume_per_well == Unit.convert_to_storage(test_value, test_unit), \
                "Plate 'max_volume_per_well' attribute does not match 'max_volume_per_well' constructor argument."
            assert test_plate.make == 'generic', \
                "Plate 'make' attribute does not match 'make' default constructor argument."
            assert test_plate.n_rows == 8, \
                "Plate 'n_rows' attribute does not match 'rows' default constructor argument."
            assert test_plate.n_columns == 12, \
                "Plate 'n_columns' attribute does not match 'columns' default constructor argument."
            assert test_plate.wells.shape == (8, 12), \
                "Plate 'wells' array size does not match 'rows/columns' default constructor arguments."
            
            # Check the first well's name to ensure it matches the expected result
            assert test_plate.wells[0,0].name == 'Well A_1', \
                "Plate's first well name did not match the expected result."

    # ==========================================================================
    # Success Case: Name, maximum volume per well, and make provided
    # ==========================================================================

    # Test single name/volume with many make combinations
    test_name = "Make Success Test"
    test_volume, test_value, test_unit = "50 mL", 50.0, 'mL'
    for test_make in test_names:
        test_plate = Plate(test_name, 
                            test_volume, 
                            make=test_make)

        # Check for correct name, max_volume_per_well, make, n_rows, n_columns,
        # and number of wells in the constructed Plate object.
        assert test_plate.name == test_name, \
            "Plate 'name' attribute does not match 'name' constructor argument."
        assert test_plate.max_volume_per_well == Unit.convert_to_storage(test_value, test_unit), \
            "Plate 'max_volume_per_well' attribute does not match 'max_volume_per_well' constructor argument."
        assert test_plate.make == test_make, \
            "Plate 'make' attribute does not match 'make' constructor argument."
        assert test_plate.n_rows == 8, \
            "Plate 'n_rows' attribute does not match 'rows' default constructor argument."
        assert test_plate.n_columns == 12, \
            "Plate 'n_columns' attribute does not match 'columns' default constructor argument."
        assert test_plate.wells.shape == (8, 12), \
                "Plate 'wells' array size does not match 'rows/columns' default constructor arguments."

        # Check the first well's name to ensure it matches the expected result
        assert test_plate.wells[0,0].name == 'Well A_1', \
            "Plate's first well name did not match the expected result."

    # ==========================================================================
    # Success Case: Name, maximum volume per well, and rows provided
    # ==========================================================================

    # Test single name/volume with many row combinations
    test_name = "Row Success Test"
    test_volume, test_value, test_unit = "20 uL", 20.0, 'uL'
    test_rows = [
        8, 1, 20, 32,
        valid_row_col_names, 
        ("A", "B", "C"),
        set(["R1", "R2", "R3", "R4"])
    ] 
    for row in test_rows:
        test_plate = Plate(test_name, 
                            test_volume, 
                            rows=row)

        test_n_rows = row if isinstance(row, int) else len(row)
        first_row = 'A' if isinstance(row, int) else (next(iter(row)))

        # Check for correct name, max_volume_per_well, make, n_rows, n_columns,
        # and number of wells in the constructed Plate object.
        assert test_plate.name == test_name, \
            "Plate 'name' attribute does not match 'name' constructor argument."
        assert test_plate.max_volume_per_well == Unit.convert_to_storage(test_value, test_unit), \
            "Plate 'max_volume_per_well' attribute does not match 'max_volume_per_well' constructor argument."
        assert test_plate.make == 'generic', \
            "Plate 'make' attribute does not match 'make' default constructor argument."
        assert test_plate.n_rows == test_n_rows, \
            "Plate 'n_rows' attribute does not match 'rows' constructor argument."
        if isinstance(row, Iterable):
            assert test_plate.row_names == row, \
                "Plate 'row_names' attribute does not match 'rows' constructor argument."
        assert test_plate.n_columns == 12, \
            "Plate 'n_columns' attribute does not match 'columns' default constructor argument."
        assert test_plate.wells.shape == (test_n_rows, 12), \
            "Plate 'wells' array size does not match 'rows/columns' constructor arguments."

        # Check the first well's name to ensure it matches the expected result
        assert test_plate.wells[0,0].name == f'Well {first_row}_1', \
            "Plate's first well name did not match the expected result."     


    # ==========================================================================
    # Success Case: Name, maximum volume per well, and columns provided
    # ==========================================================================

    # Test single name/volume with many column combinations
    test_name = "Column Success Test"
    test_volume, test_value, test_unit = "30 uL", 30.0, 'uL'
    test_columns = [
        12, 1, 30, 48,
        valid_row_col_names, 
        ("1", "2", "3"),
        set(["C1", "C2", "C3", "C4"])
    ] 
    for col in test_columns:
        test_plate = Plate(test_name, 
                            test_volume, 
                            columns=col)

        test_n_cols = col if isinstance(col, int) else len(col)
        first_column = '1' if isinstance(col, int) else (next(iter(col)))

        # Check for correct name, max_volume_per_well, make, n_rows, n_columns,
        # and number of wells in the constructed Plate object.
        assert test_plate.name == test_name, \
            "Plate 'name' attribute does not match 'name' constructor argument."
        assert test_plate.max_volume_per_well == Unit.convert_to_storage(test_value, test_unit), \
            "Plate 'max_volume_per_well' attribute does not match 'max_volume_per_well' constructor argument."
        assert test_plate.make == 'generic', \
            "Plate 'make' attribute does not match 'make' default constructor argument."
        assert test_plate.n_rows == 8, \
            "Plate 'n_rows' attribute does not match 'rows' default constructor argument."
        assert test_plate.n_columns == test_n_cols, \
            "Plate 'n_columns' attribute does not match 'columns' constructor argument."
        if isinstance(col, Iterable):
            assert test_plate.column_names == col, \
                "Plate 'column_names' attribute does not match 'cols' constructor argument."
        assert test_plate.wells.shape == (8, test_n_cols), \
            "Plate 'wells' array size does not match 'rows/columns' constructor arguments."

        # Check the first well's name to ensure it matches the expected result
        assert test_plate.wells[0,0].name == f'Well A_{first_column}', \
            "Plate's first well name did not match the expected result."  


    # ==========================================================================
    # Success Case: All arguments provided
    # ==========================================================================
    
    # Test single name/volume/make combination with a few different options for
    # rows and columns.
    test_name = "Full Success Test"
    test_volume, test_value, test_unit = "100 L", 100.0, 'L'
    test_make = "ACME Corporation"
    test_rows = [
        8, 32,
        ["Water", "H2SO4", "DMSO", "Methanol", "THF", 
         "Empty 1", "Empty 2", "Empty 3"]
    ]
    test_columns = [
        12, 48,
        [f"Ligand-{i + 1}" for i in range(12)]
    ]

    for row, col in product(test_rows, test_columns):
        test_plate = Plate(test_name, 
                            test_volume,
                            make=test_make,
                            rows=row,
                            columns=col)

        test_n_rows = row if isinstance(row, int) else len(row)
        first_row = 'A' if isinstance(row, int) else (next(iter(row)))
        test_n_cols = col if isinstance(col, int) else len(col)
        first_column = '1' if isinstance(col, int) else (next(iter(col)))

        # Check for correct name, max_volume_per_well, make, n_rows, n_columns,
        # and number of wells in the constructed Plate object.
        assert test_plate.name == test_name, \
            "Plate 'name' attribute does not match 'name' constructor argument."
        assert test_plate.max_volume_per_well == Unit.convert_to_storage(test_value, test_unit), \
            "Plate 'max_volume_per_well' attribute does not match 'max_volume_per_well' constructor argument."
        assert test_plate.make == test_make, \
            "Plate 'make' attribute does not match 'make' constructor argument."
        
        assert test_plate.n_rows == test_n_rows, \
            "Plate 'n_rows' attribute does not match 'rows' constructor argument."
        if isinstance(row, Iterable):
            assert test_plate.row_names == row, \
                "Plate 'row_names' attribute does not match 'rows' constructor argument."
       
        assert test_plate.n_columns == test_n_cols, \
            "Plate 'n_columns' attribute does not match 'columns' constructor argument."
        if isinstance(col, Iterable):
            assert test_plate.column_names == col, \
                "Plate 'column_names' attribute does not match 'cols' constructor argument."
        
        assert test_plate.wells.shape == (test_n_rows, test_n_cols), \
            "Plate 'wells' array size does not match 'rows/columns' constructor arguments."

        # Check the first well's name to ensure it matches the expected result
        assert test_plate.wells[0,0].name == f'Well {first_row}_{first_column}', \
            "Plate's first well name did not match the expected result."   

    
def test_Plate___getitem__(empty_plate:Plate,
                           water_plate:Plate):
    """
    Unit test for `Plate.__get_item__()`.

    This unit test is only present to ensure the function is defined and returns
    a value for both Plate fixtures; the functionality is tested by the unit 
    test for the PlateSlicer constructor.
    """
    assert empty_plate[1,1] is not None
    assert water_plate[1,1] is not None


def test_Plate___repr__(empty_plate:Plate,
                        water_plate:Plate):
    """
    Unit test for `Plate.__repr__()`.

    At present, there are no specific requirements for the string representation
    of a `Plate` object. This unit test simply checks that the function returns
    a value for both Plate fixtures.
    """

    assert empty_plate.__repr__() is not None
    assert water_plate.__repr__() is not None


def test_Plate_get_volumes(empty_plate:Plate,
                           water_plate:Plate):
    """
    Unit test for `Plate.get_volumes()`.

    This is a minimal unit test which ensures the function is defined and 
    returns reasonable results for both Plate fixtures; the functionality is 
    robustly tested by the unit test for `PlateSlicer.get_volumes()`.
    """

    empty_volumes = empty_plate.get_volumes()  
    assert empty_volumes is not None
    assert numpy.all(empty_volumes == 0), \
        "Not all volumes in empty_plate are zero."

    water_volumes = water_plate.get_volumes()
    assert water_volumes is not None
    assert numpy.all(water_volumes > 0), \
        "Not all volumes in water_plate are greater than zero."


def test_Plate_get_substances(empty_plate:Plate, 
                              water_plate:Plate,
                              water:Substance):
    """
    Unit test for `Plate.get_substances()`.

    This is a minimal unit test which ensures the function is defined and 
    returns reasonable results for both Plate fixtures; the functionality is 
    robustly tested by the unit test for `PlateSlicer.get_substances()`.
    """

    empty_substances = empty_plate.get_substances()
    assert empty_substances is not None
    assert len(empty_substances) == 0, \
        "Substances were incorrectly returned for the empty plate."

    water_plate_substances = water_plate.get_substances()
    assert water_plate_substances is not None
    assert len(water_plate_substances) != 0, \
        "No substances were returned for the water plate."
    assert len(water_plate_substances) == 1, \
        "More than one substance was returned for the water plate."
    assert water in water_plate_substances, \
        "Water was not found in the substances of the water plate."
    

def test_Plate_get_moles(empty_plate:Plate, 
                         water_plate:Plate,
                         water:Substance):
    """
    Unit test for `Plate.get_moles()`.

    This is a minimal unit test which ensures the function is defined and 
    returns reasonable results for both Plate fixtures; the functionality is 
    robustly tested by the unit test for `PlateSlicer.get_moles()`.
    """

    # TODO: Come back and rework these if/when PlateSlicer.get_moles() is 
    # refactored

    empty_moles = empty_plate.get_moles(water)  
    assert empty_moles is not None
    assert numpy.all(empty_moles == 0), \
        "Not all moles in empty_plate are zero."

    water_moles = water_plate.get_moles(water)
    assert water_moles is not None
    assert numpy.all(water_moles > 0), \
        "Not all moles in water_plate are greater than zero."



# def test_volume_and_volumes(salt, water, dmso, empty_plate):
#     """

#     Test get_volume() and get_volumes() for a plate.

#     """
#     epsilon = 1e-3
#     with pytest.raises(TypeError, match="Substance must be a Substance"):
#         empty_plate.get_volumes('1')

#     zeros = numpy.zeros(empty_plate.wells.shape)
#     uL = numpy.ones(empty_plate.wells.shape)
#     config.precisions['uL'] = 3
#     # set precision to 3 decimal places for 'uL' for testing

#     salt_volume = round(salt.convert_quantity('5 umol', 'uL'), 3)
#     assert empty_plate.get_volume() == 0
#     assert numpy.array_equal(empty_plate.get_volumes(), zeros)
#     assert numpy.array_equal(empty_plate.get_volumes(water), zeros)

#     salt_container = Container('salt', initial_contents=((salt, '1 mol'),))
#     salt_container, new_plate = Plate.transfer(salt_container, empty_plate, '5 umol')
#     assert new_plate.get_volume() == pytest.approx((salt_volume * uL).sum(), epsilon)
#     assert numpy.allclose(new_plate.get_volumes(unit='uL'), salt_volume * uL)
#     assert numpy.array_equal(new_plate.get_volumes(water), zeros)
#     assert numpy.allclose(new_plate.get_volumes(salt, unit='uL'), salt_volume * uL, atol=epsilon)

#     water_container = Container('water', initial_contents=((water, '1 L'),))
#     water_container, new_plate = Plate.transfer(water_container, new_plate, '50 uL')
#     assert new_plate.get_volume() == pytest.approx((salt_volume * uL).sum() + (50 * uL).sum(), epsilon)
#     assert numpy.allclose(new_plate.get_volumes(), (salt_volume + 50) * uL)
#     assert numpy.allclose(new_plate.get_volumes(water), 50 * uL)
#     assert numpy.allclose(new_plate.get_volumes(salt), salt_volume * uL, atol=1e-3)

#     dmso_container = Container('dmso', initial_contents=((dmso, '1 L'), ))
#     dmso_container, new_plate = Plate.transfer(dmso_container, new_plate, '25 uL')
#     assert new_plate.get_volume() == pytest.approx((salt_volume * uL).sum() + (75 * uL).sum(), epsilon)
#     assert numpy.allclose(new_plate.get_volumes(), (salt_volume + 75) * uL)
#     assert numpy.allclose(new_plate.get_volumes(water), 50 * uL)
#     assert numpy.allclose(new_plate.get_volumes(dmso), 25 * uL)
#     assert numpy.allclose(new_plate.get_volumes(salt), salt_volume * uL, atol=epsilon)
#     assert numpy.allclose(new_plate.get_volumes(water, unit='mL'), 0.05 * uL)


# def test_moles(salt, water, empty_plate):
#     """

#     Test moles() for a plate.

#     """
#     with pytest.raises(TypeError, match="Substance must be a Substance"):
#         empty_plate.get_moles('1')

#     zeros = numpy.zeros(empty_plate.wells.shape)
#     ones = numpy.ones(empty_plate.wells.shape)
#     assert numpy.array_equal(empty_plate.get_moles(salt), zeros)

#     salt_container = Container('salt', initial_contents=((salt, '1 mol'),))
#     salt_container, new_plate = Plate.transfer(salt_container, empty_plate, '5 umol')
#     assert numpy.array_equal(new_plate.get_moles(salt, 'umol'), 5 * ones)
#     assert numpy.array_equal(new_plate.get_moles(water), zeros)

#     water_container = Container('water', initial_contents=((water, '1 L'),))
#     water_container, new_plate = Plate.transfer(water_container, new_plate, '1 mmol')
#     assert numpy.array_equal(new_plate.get_moles(salt, 'umol'), 5 * ones)
#     assert numpy.array_equal(new_plate.get_moles(water, unit='mmol'), ones)

#     water_container = Container('water', initial_contents=((water, '1 L'),))
#     water_container, new_plate = Plate.transfer(water_container, new_plate, '5 uL')
#     new_plate.get_moles(water)
