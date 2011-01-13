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

# the following code is stolen from github-tools (Damien Lebrun, BSD-style license)

    app.connect('html-page-context', change_pathto)
    app.connect('build-finished', move_private_folders)

import os
import shutil

def change_pathto(app, pagename, templatename, context, doctree):
    """
    Replace pathto helper to change paths to folders with a leading underscore.
    """
    pathto = context.get('pathto')
    def gh_pathto(otheruri, *args, **kw):
        if otheruri.startswith('_'):
            otheruri = otheruri[1:]
        return pathto(otheruri, *args, **kw)
    context['pathto'] = gh_pathto

def move_private_folders(app, e):
    """
    remove leading underscore from folders in in the output folder.

    :todo: should only affect html built
    """
    def join(dir):
        return os.path.join(app.builder.outdir, dir)

    for item in os.listdir(app.builder.outdir):
        if item.startswith('_') and os.path.isdir(join(item)):
            shutil.move(join(item), join(item[1:]))
