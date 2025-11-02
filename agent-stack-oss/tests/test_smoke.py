def test_import():
    import src.agent.graph as g
    assert callable(g.build_graph)
