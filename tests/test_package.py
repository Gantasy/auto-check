def test_package_version_exists():
    from codecheck_shield import __version__

    assert __version__ == "1.0.0"
