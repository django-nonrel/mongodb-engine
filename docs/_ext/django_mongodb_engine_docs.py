def setup(app):
    from docutils.parsers.rst.directives.admonitions import Note

    app.add_directive('forthelazy', Note) # for now

    app.add_crossref_type(
        directivename="setting",
        rolename="setting",
        indextemplate="pair: %s; setting",
    )
    app.add_crossref_type(
        directivename="sig",
        rolename="sig",
        indextemplate="pair: %s; sig",
    )
    app.add_crossref_type(
        directivename="state",
        rolename="state",
        indextemplate="pair: %s; state",
    )
    app.add_crossref_type(
        directivename="control",
        rolename="control",
        indextemplate="pair: %s; control",
    )
