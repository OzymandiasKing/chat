"""Tinode command line macro definitions."""

import argparse
import tn_globals
from tn_globals import stdoutln


class Macro:
    """Macro base class. The external callers are expected to access
    * self.parser - an instance of argparse.Argument parser which attempts to
      turn a list of tokens into the corresponding argparse command.
    * self.run() - executes the macro as instructed by the user."""

    def __init__(self):
        self.parser = argparse.ArgumentParser(prog=self.name(), description=self.description())
        self.add_parser_args()
        # Explain argument.
        self.parser.add_argument('--explain', action='store_true', help='Only print out expanded macro') 
    def name(self):
        """Macro name."""
        pass

    def description(self):
        """Macro description."""
        pass

    def add_parser_args(self):
        """Method which adds custom command line arguments."""
        pass

    def expand(self, id, cmd, args):
        """Expands the macro to a list of basic Tinode CLI commands."""
        pass

    def run(self, id, cmd, args):
        """Expands the macro and returns the list of commands to actually execute to the caller
        depending on the presence of the --explain argument.
        """
        cmds = self.expand(id, cmd, args)
        if cmd.explain:
            if cmds is None:
                return None
            for item in cmds:
                stdoutln(item)
            return []
        return cmds


class Usermod(Macro):
    """Modifies user account. The following modes are available:
    * suspend/unsuspend account.
    * change user's VCard (public name, avatar, private comment).

    This macro requires root privileges."""

    def name(self):
        return "usermod"

    def description(self):
        return 'Modify user account (requires root privileges)'

    def add_parser_args(self):
        self.parser.add_argument('userid', help='user to update')
        self.parser.add_argument('-L', '--suspend', action='store_true', help='Suspend account')
        self.parser.add_argument('-U', '--unsuspend', action='store_true', help='Unsuspend account')
        self.parser.add_argument('--name', help='Public name')
        self.parser.add_argument('--avatar', help='Avatar file name')
        self.parser.add_argument('--comment', help='Private comment on account') 

    def expand(self, id, cmd, args):
        if not cmd.userid:
            return None

        # Suspend/unsuspend user.
        if cmd.suspend or cmd.unsuspend:
            if cmd.suspend and cmd.unsuspend:
                stdoutln("Cannot both suspend and unsuspend account")
                return None
            new_cmd = 'acc --user %s' % cmd.userid
            if cmd.suspend:
                new_cmd += ' --suspend true'
            if cmd.unsuspend:
                new_cmd += ' --suspend false'
            return [new_cmd]
        # Change VCard.
        set_cmd = 'set me'
        if cmd.name:
            set_cmd += ' --fn="%s"' % cmd.name
        if cmd.avatar:
            set_cmd += ' --photo="%s"' % cmd.avatar
        if cmd.comment:
            set_cmd += ' --private="%s"' % cmd.comment
        if tn_globals.DefaultUser:
            old_user = tn_globals.DefaultUser
        else:
            old_user = ''
        return ['.use --user %s' % cmd.userid,
                '.must sub me', set_cmd,
                '.must leave me',
                '.use --user \'%s\'' % old_user]


class Resolve(Macro):
    """Looks up user id by login name and prints it."""

    def name(self):
        return "resolve"

    def description(self):
        return "Resolve login and print the corresponding user id"

    def add_parser_args(self):
        self.parser.add_argument('login', help='login to resolve')

    def expand(self, id, cmd, args):
        if not cmd.login:
            return None

        return ['.must sub fnd',
                '.must set fnd --public=basic:%s' % cmd.login,
                '.must $userid get fnd --sub',
                '.must leave fnd',
                '.log $userid.sub[0].user_id']


class Passwd(Macro):
    """Sets user's password (requires root privileges)."""

    def name(self):
        return "passwd"

    def description(self):
        return "Set user's password (requires root privileges)"

    def add_parser_args(self):
        self.parser.add_argument('userid', help='Id of the user')
        self.parser.add_argument('-P', '--password', help='New password')

    def expand(self, id, cmd, args):
        if not cmd.userid:
            return None

        if not cmd.password:
            stdoutln("Password (-P) not specified")
            return None

        return ['acc --user %s --scheme basic --secret :%s' % (cmd.userid, cmd.password)]


class Useradd(Macro):
    """Creates a new user account."""

    def name(self):
        return "useradd"

    def description(self):
        return "Create a new user account"

    def add_parser_args(self):
        self.parser.add_argument('login', help='User login')
        self.parser.add_argument('-P', '--password', help='Password')
        self.parser.add_argument('--cred', help='C')
        self.parser.add_argument('--name', help='C')
        self.parser.add_argument('--comment', help='C')
        self.parser.add_argument('--tags', help='C')
        self.parser.add_argument('--avatar', help='C')
        self.parser.add_argument('--auth', help='C')
        self.parser.add_argument('--anon', help='C')

    def expand(self, id, cmd, args):
        if not cmd.login:
            return None
        if not cmd.password:
            stdoutln("Password --password must be specified")
            return None
        if not cmd.cred:
            stdoutln("Must specify at least one credential: --cred.")
            return None
        new_cmd = 'acc --scheme basic --secret=%s:%s --cred=%s' % (cmd.login, cmd.password, cmd.cred)
        if cmd.name:
            new_cmd += ' --fn=%s' % cmd.name
        if cmd.comment:
            new_cmd += ' --private=%s' % cmd.comment
        if cmd.tags:
            new_cmd += ' --tags=%s' % cmd.tags
        if cmd.avatar:
            new_cmd += ' --photo=%s' % cmd.avatar
        if cmd.auth:
            new_cmd += ' --auth=%s' % cmd.auth
        if cmd.anon:
            new_cmd += ' --anon=%s' % cmd.anon
        return [new_cmd]


class Chacs(Macro):
    """Modifies default acs (permissions) on a user account."""

    def name(self):
        return "chacs"

    def description(self):
        return "Change default permissions/acs for a user"

    def add_parser_args(self):
        self.parser.add_argument('userid', help='User id')
        self.parser.add_argument('--auth', help='C')
        self.parser.add_argument('--anon', help='C')

    def expand(self, id, cmd, args):
        if not cmd.userid:
            return None
        if not cmd.auth and not cmd.anon:
            stdoutln('Must specify at least either of --auth, --anon')
            return None
        set_cmd = '.must set me'
        if cmd.auth:
            set_cmd += ' --auth=%s' % cmd.auth
        if cmd.anon:
            set_cmd += ' --anon=%s' % cmd.anon
        if tn_globals.DefaultUser:
            old_user = tn_globals.DefaultUser
        else:
            old_user = ''
        return ['.use --user %s' % cmd.userid,
                '.must sub me', set_cmd,
                '.must leave me',
                '.use --user \'%s\'' % old_user]


def parse_macro(parts):
    """Attempts to find a parser for the provided sequence of tokens."""
    global Macros
    # parts[0] is the command.
    macro = Macros.get(parts[0])
    if not macro:
        return None
    return macro.parser


Macros = {x.name(): x for x in [Usermod(), Resolve(), Passwd(), Useradd(), Chacs()]}
