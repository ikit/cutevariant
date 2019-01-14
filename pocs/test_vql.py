
import pytest
from pprint import pprint
from vql import model_from_string, VQLSyntaxError
from vql import AND, OR, EQ, NE, LT


# Test valid VQL cases
VQL_TO_TREE_CASES = {
    'SELECT chr,pos,gt("sacha").gt FROM variants': {
        'select': ('chr', 'pos', 'gt("sacha").gt'),
        'from': 'variants',
    },
    'SELECT chr,pos,ref FROM variants WHERE a=3 AND b=/=5 AND c<3': {
        'select': ('chr', 'pos', 'ref'),
        'from': 'variants',
        'where': {AND: ({'field': 'a', 'operator': EQ, 'value': 3},
                        {'field': 'b', 'operator': NE, 'value': 5},
                        {'field': 'c', 'operator': LT, 'value': 3})},
    },
    'SELECT chr,pos,ref FROM variants WHERE a=3 AND (b=5 OR c=3)': {
        'select': ('chr', 'pos', 'ref'),
        'from': 'variants',
        'where': {AND: ({'field': 'a', 'operator': EQ, 'value': 3},
                        {OR: ( {'field': 'b', 'operator': EQ, 'value': 5},
                               {'field': 'c', 'operator': EQ, 'value': 3})})},
    },
    'SELECT chr,pos, gt("sacha").gt FROM variants USING file.bed # Next feature': {
        'select': ('chr', 'pos', 'gt("sacha").gt'),
        'from': 'variants',
        'using': ('file.bed',),
    },
}

def template_test_case(vql_expr:str, expected:dict) -> callable:
    "Return a function that test equivalence between given VQL and expected result"

    def test_function():
        found = model_from_string(vql_expr)
        print('EXPECTED:', ', '.join(sorted(tuple(expected.keys()))))
        pprint(expected)
        print()
        print('FOUND:', ', '.join(sorted(tuple(found.keys()))))
        pprint(found)
        assert found == expected

    return test_function

# generate all test cases
for idx, (vql, expected) in enumerate(VQL_TO_TREE_CASES.items(), start=1):
    globals()[f'test_vql_{idx}'] = template_test_case(vql, expected)


# test exceptions returned by VQL
MALFORMED_VQL_CASES = {
    # '': ('no select clause',),
    # 'SELECT chr,pos,ref FROM': ('empty \'FROM\' clause',),
    # 'SELECT chr,,ref FROM': ('invalid identifier \'\' in SELECT clause',),
}

def template_test_malformed_case(vql_expr:str, expected:tuple) -> callable:
    "Return a function that test equivalence between given VQL and expected result"

    def test_function():
        with pytest.raises(VQLSyntaxError) as excinfo:
            model_from_string(vql_expr)
        assert excinfo.value == expected

    return test_function

# generate all test cases
for idx, (vql, expected) in enumerate(MALFORMED_VQL_CASES.items(), start=1):
    globals()[f'test_malformed_vql_{idx}'] = template_test_malformed_case(vql, expected)