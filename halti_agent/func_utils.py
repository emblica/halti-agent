"""
Small functional helpers.
"""


def diff(a, b):
    """Compares a and b, returning a tuple of
    (things-only-in-a, things-only-in-b, things-in-both).
    """
    return (
        set(a) - set(b),
        set(b) - set(a),
        set(a) & set(b)
    )


def env_pairs_to_dict(env_list):
    """Flatten a list of env_pairs ({'key':foo, 'value': bar}) to a dict."""
    return {
        env_pair['key']: env_pair['value']
        for env_pair in env_list
    }
