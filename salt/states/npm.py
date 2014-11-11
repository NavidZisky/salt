# -*- coding: utf-8 -*-
'''
Installation of NPM Packages
============================

These states manage the installed packages for node.js using the Node Package
Manager (npm). Note that npm must be installed for these states to be
available, so npm states should include a requisite to a pkg.installed state
for the package which provides npm (simply ``npm`` in most cases). Example:

.. code-block:: yaml

    npm:
      pkg.installed

    yaml:
      npm.installed:
        - require:
          - pkg: npm
'''
from __future__ import absolute_import

# Import salt libs
from salt.exceptions import CommandExecutionError, CommandNotFoundError


def __virtual__():
    '''
    Only load if the npm module is available in __salt__
    '''
    return 'npm' if 'npm.list' in __salt__ else False


def installed(name,
              pkgs=None,
              dir=None,
              user=None,
              force_reinstall=False,
              registry=None,
              env=None):
    '''
    Verify that the given package is installed and is at the correct version
    (if specified).

    .. code-block:: yaml

        coffee-script:
          npm:
            - installed
            - user: someuser

        coffee-script@1.0.1:
          npm:
            - installed

    name
        The package to install

    pkgs
        A list of packages to install with a single npm invocation; specifying
        this argument will ignore the ``name`` argument

        .. versionadded:: 2014.7.0

    dir
        The target directory in which to install the package, or None for
        global installation

    user
        The user to run NPM with

        .. versionadded:: 0.17.0

    registry
        The NPM registry from which to install the package

        .. versionadded:: 2014.7.0

    env
        A list of environment variables to be set prior to execution. The
        format is the same as the :py:func:`cmd.run <salt.states.cmd.run>`.
        state function.

        .. versionadded:: 2014.7.0

    force_reinstall
        Install the package even if it is already installed
    '''
    ret = {'name': name, 'result': None, 'comment': '', 'changes': {}}

    if pkgs is not None:
        pkg_list = pkgs
    else:
        pkg_list = [name]

    try:
        installed_pkgs = __salt__['npm.list'](dir=dir, runas=user, env=env)
    except (CommandNotFoundError, CommandExecutionError) as err:
        ret['result'] = False
        ret['comment'] = 'Error looking up {0!r}: {1}'.format(name, err)
        return ret
    else:
        installed_pkgs = dict((p.lower(), info)
                for p, info in list(installed_pkgs.items()))

    pkgs_satisfied = []
    pkgs_to_install = []
    for pkg in pkg_list:
        pkg_name, _, pkg_ver = pkg.partition('@')
        pkg_name = pkg_name.strip().lower()

        if force_reinstall is True:
            pkgs_to_install.append(pkg)
            continue

        if pkg_name not in installed_pkgs:
            pkgs_to_install.append(pkg)
            continue

        if pkg_name in installed_pkgs:
            installed_name_ver = '{0}@{1}'.format(pkg_name,
                    installed_pkgs[pkg_name]['version'])

            # If given an explicit version check the installed version matches.
            if pkg_ver:
                if installed_pkgs[pkg_name].get('version') != pkg_ver:
                    pkgs_to_install.append(pkg)
                else:
                    pkgs_satisfied.append(installed_name_ver)

                continue
            else:
                pkgs_satisfied.append(installed_name_ver)
                continue

    if __opts__['test']:
        ret['result'] = None

        comment_msg = []
        if pkgs_to_install:
            comment_msg.append('NPM package(s) {0!r} are set to be installed'
                .format(', '.join(pkgs_to_install)))

            ret['changes'] = {'old': [], 'new': pkgs_to_install}

        if pkgs_satisfied:
            comment_msg.append('Package(s) {0!r} satisfied by {1}'
                .format(', '.join(pkg_list), ', '.join(pkgs_satisfied)))

        ret['comment'] = '. '.join(comment_msg)
        return ret

    if not pkgs_to_install:
        ret['result'] = True
        ret['comment'] = ('Package(s) {0!r} satisfied by {1}'
                .format(', '.join(pkg_list), ', '.join(pkgs_satisfied)))
        return ret

    try:
        cmd_args = {
            'dir': dir,
            'runas': user,
            'registry': registry,
            'env': env,
        }

        if pkgs is not None:
            cmd_args['pkgs'] = pkgs
        else:
            cmd_args['pkg'] = pkg_name

        call = __salt__['npm.install'](**cmd_args)
    except (CommandNotFoundError, CommandExecutionError) as err:
        ret['result'] = False
        ret['comment'] = 'Error installing {0!r}: {1}'.format(
                ', '.join(pkg_list), err)
        return ret

    if call and (isinstance(call, list) or isinstance(call, dict)):
        ret['result'] = True
        ret['changes'] = {'old': [], 'new': pkgs_to_install}
        ret['comment'] = 'Package(s) {0!r} successfully installed'.format(
                ', '.join(pkgs_to_install))
    else:
        ret['result'] = False
        ret['comment'] = 'Could not install package(s) {0!r}'.format(
                ', '.join(pkg_list))

    return ret


def removed(name,
            dir=None,
            user=None):
    '''
    Verify that the given package is not installed.

    dir
        The target directory in which to install the package, or None for
        global installation

    user
        The user to run NPM with

        .. versionadded:: 0.17.0
    '''
    ret = {'name': name, 'result': None, 'comment': '', 'changes': {}}

    try:
        installed_pkgs = __salt__['npm.list'](dir=dir)
    except (CommandExecutionError, CommandNotFoundError) as err:
        ret['result'] = False
        ret['comment'] = 'Error uninstalling {0!r}: {1}'.format(name, err)
        return ret

    if name not in installed_pkgs:
        ret['result'] = True
        ret['comment'] = 'Package {0!r} is not installed'.format(name)
        return ret

    if __opts__['test']:
        ret['result'] = None
        ret['comment'] = 'Package {0!r} is set to be removed'.format(name)
        return ret

    if __salt__['npm.uninstall'](pkg=name, dir=dir, runas=user):
        ret['result'] = True
        ret['changes'][name] = 'Removed'
        ret['comment'] = 'Package {0!r} was successfully removed'.format(name)
    else:
        ret['result'] = False
        ret['comment'] = 'Error removing package {0!r}'.format(name)

    return ret


def bootstrap(name,
              user=None):
    '''
    Bootstraps a node.js application.

    Will execute 'npm install --json' on the specified directory.

    user
        The user to run NPM with

        .. versionadded:: 0.17.0
    '''
    ret = {'name': name, 'result': None, 'comment': '', 'changes': {}}

    try:
        call = __salt__['npm.install'](dir=name, runas=user, pkg=None)
    except (CommandNotFoundError, CommandExecutionError) as err:
        ret['result'] = False
        ret['comment'] = 'Error Bootstrapping {0!r}: {1}'.format(name, err)
        return ret

    if not call:
        ret['result'] = True
        ret['comment'] = 'Directory is already bootstrapped'
        return ret

    # npm.install will return a string if it can't parse a JSON result
    if isinstance(call, str):
        ret['result'] = False
        ret['comment'] = 'Could not bootstrap directory'
    else:
        ret['result'] = True
        ret['changes'] = {name: 'Bootstrapped'}
        ret['comment'] = 'Directory was successfully bootstrapped'

    return ret
