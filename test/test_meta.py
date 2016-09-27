from halti_agent.func_utils import diff


def test_diff():
    """test diff works on sets, keys of dicts and lists."""
    a = {'a', 'b'}
    b = {'b': 1, 'c': 2}

    only_a, only_b, both = diff(a, b)

    assert {'a'} == only_a
    assert {'c'} == only_b
    assert {'b'} == both

    c = ['c', 'd']
    only_b, only_d, both = diff(b, c)
    assert {'b'} == only_b
    assert {'d'} == only_d
    assert {'c'} == both
