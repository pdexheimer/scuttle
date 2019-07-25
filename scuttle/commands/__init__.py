# scuttle - manage and manipulate sc-rna data files
# Copyright (C) 2019 Phillip Dexheimer

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import logging
import sys

from scuttle.commands import annotate, describe, help, select


def add_subcommands_to_parser(parser):
    annotate.add_to_parser(parser)
    describe.add_to_parser(parser)
    select.add_to_parser(parser)
    help.add_to_parser(parser)


class CommandParser:
    """
    Replacement for ArgParser that supports stringing together verbs into a single command line
    """

    def __init__(self):
        self.verbs = []
        self.global_opts = []
        self._tokens = {}
        self._help = None

    def add_verb(self, verb):
        subcommand = CommandLineVerb(verb)
        self.verbs.append(subcommand)
        self._tokens[verb] = subcommand
        return subcommand

    def add_global_option(self, name, *args, **kwargs):
        option = CommandLineOption(name, *args, **kwargs)
        for arg in option.all_names:
            if arg in self._tokens:
                raise DuplicateArgumentError(arg, 'global')
            self._tokens[arg] = option
        self.global_opts.append(option)

    @property
    def help(self):
        if self._help is None:
            self._help = self.add_verb('help')
        return self._help

    def default_namespace(self):
        namespace = Namespace()
        for opt in self.global_opts:
            opt._set_defaults(namespace)
        return namespace

    @staticmethod
    def _parse_option(option, argv, namespace):
        """
        Consume the appropriate words from argv and parse option into the namespace
        """
        if option.nargs > len(argv):
            raise ValueError
        opt_args = argv[:option.nargs]
        del argv[:option.nargs]
        option.parse(opt_args, namespace)

    def parse(self, argv=None):
        self._ensure_verbs_are_complete()
        if argv is None:
            argv = sys.argv[1:]
        global_namespace = self.default_namespace()
        commands = []
        while argv:
            arg = argv.pop(0)
            if arg not in self._tokens:
                logging.critical(f"Unrecognized argument '{arg}'")
                exit(1)
            parameter = self._tokens[arg]
            if isinstance(parameter, CommandLineVerb):
                (parsed_args, global_namespace) = parameter.parse(argv, self.global_opts, global_namespace)
                if parameter == self._help:
                    # If there's a help command, it should be the only command processed
                    return None, [CommandRun(parsed_args, parameter._execute_verb)]
                commands.append(CommandRun(parsed_args, parameter._execute_verb))
            if isinstance(parameter, CommandLineOption):
                CommandParser._parse_option(parameter, argv, global_namespace)
        return (global_namespace, commands)

    def _ensure_verbs_are_complete(self):
        for verb in self.verbs:
            if verb._execute_verb is None:
                logging.critical(f"No execution specified for '{verb.verb}'."
                                 ' Make sure you call set_executor() before parse()')
                exit(1)


class CommandLineVerb:
    """
    A "command" on the command line, conceptually built around a single verb.
    For instance, in git, 'commit' and 'log' are verbs that unlock a separate suite of options.

    Typically created by calling CommandParser::add_verb()
    """

    def __init__(self, verb):
        self.verb = verb
        self.options = []
        self.arguments = []
        self.subcommands = []
        self._tokens = {'subcommand': None}
        self._execute_verb = None
        self._validate_args = None

    def add_option(self, name, *args, **kwargs):
        option = CommandLineOption(name, *args, **kwargs)
        for arg in option.all_names:
            if arg in self._tokens:
                raise DuplicateArgumentError(arg, self.verb)
            self._tokens[arg] = option
        self.options.append(option)

    def add_argument(self, name):
        self.arguments.append(name)

    def add_verb(self, verb):
        subcommand = CommandLineVerb(verb)
        self.subcommands.append(subcommand)
        self._tokens[verb] = subcommand
        return subcommand

    def set_executor(self, exe_function):
        self._execute_verb = exe_function

    def set_validator(self, validate_function):
        self._validate_args = validate_function

    def default_namespace(self):
        namespace = Namespace()
        self.add_defaults(namespace)
        return namespace

    def add_defaults(self, namespace):
        for opt in self.options:
            opt._set_defaults(namespace)
        if self.subcommands:
            namespace.subcommand = None

    def parse(self, argv, global_options, global_namespace, namespace=None):
        """
        Parses words from argv, stopping when it reaches an unrecognized
        argument (ie, not specified in this Verb or in the global_options).

        Returns a tuple of namespaces.  The first is for this verb, the second
        is the global namespace.  Before returning, the function supplied via
        set_validator() (if any) will be run on the parsed namespace
        """

        if namespace is None:
            namespace = self.default_namespace()
        global_lookup = {}
        for opt in global_options:
            for name in opt.all_names:
                if name in self._tokens:
                    raise DuplicateArgumentError(name, self.verb)
                global_lookup[name] = opt
        parsed_arguments = 0
        while argv:
            lookahead = argv[0]
            if lookahead in global_lookup:
                argv.pop(0)
                CommandParser._parse_option(global_lookup[lookahead], argv, global_namespace)
                continue
            if lookahead not in self._tokens:
                # If it's not a global option and it's not in _tokens, it's either an argument
                # or it's not recognized.  Check how many args have already been processed
                if parsed_arguments >= len(self.arguments):
                    return (namespace, global_namespace)
                setattr(namespace, self.arguments[parsed_arguments], lookahead)
                argv.pop(0)
                parsed_arguments += 1
                continue
            # At this point, we know that the lookahead is in our _tokens dictionary
            parameter = self._tokens[lookahead]
            argv.pop(0)
            if isinstance(parameter, CommandLineVerb):
                namespace.subcommand = parameter.verb
                parameter.add_defaults(namespace)
                return parameter.parse(argv, global_options, global_namespace, namespace)
            if isinstance(parameter, CommandLineOption):
                CommandParser._parse_option(parameter, argv, namespace)
        if parsed_arguments < len(self.arguments):
            logging.critical(f'[{self.verb}] Missing {len(self.arguments) - parsed_arguments} required arguments')
            exit(1)
        if self._validate_args is not None:
            self._validate_args(namespace)
        return (namespace, global_namespace)


class CommandLineOption:
    """
    An encapsulation of a command line option -- ie, a parameter prefixed with a dash
    that may include parameters specified after it
    """

    def __init__(self, name, *alt_names, destvar=None, nargs=1, action='store', default=None, type=str, choices=None):
        self.name = name
        if destvar is None:
            raise ValueError
        self.all_names = [name, *alt_names]
        self.destvar = destvar
        self.nargs = nargs
        self.action = action
        self.default = default
        self.type = type
        self.choices = None if choices is None else set(choices)
        if action == 'store_true':
            self.default = False
            self.type = bool
            self.nargs = 0
        elif action == 'store_false':
            self.default = True
            self.type = bool
            self.nargs = 0

    def _set_defaults(self, namespace):
        setattr(namespace, self.destvar, self.default if self.default is None else self.type(self.default))

    def parse(self, args, namespace):
        value = None
        if self.action == 'store_true':
            value = True
        elif self.action == 'store_false':
            value = False
        else:
            try:
                value = self.validate([self.type(x) for x in args])
            except ValueError:
                raise
            if len(value) == 1:
                value = value[0]
        setattr(namespace, self.destvar, value)

    def validate(self, values):
        if self.choices is None:
            return values
        for val in values:
            if val not in self.choices:
                logging.critical(f"Invalid option for {self.name} ({val}).  Valid choices are {','.join(self.choices)}")
                exit(1)
        return values


class CommandRun:
    """
    Encapsulates the parsed arguments for a particular CommandLineVerb, along with
    the function that will actually do something with them.  This is what's returned from
    CommandParser.parse()
    """

    def __init__(self, args, runner):
        self.args = args
        self.runner = runner

    def execute(self, *args, **kwargs):
        self.runner(self.args, *args, **kwargs)


class DuplicateArgumentError(Exception):
    """
    Ambiguous arguments have been specified for a CommandParser
    """

    def __init__(self, arg_name, context):
        self.duplicate_argument = arg_name
        self.duplicate_context = context


class Namespace:
    """
    A dummy object that's used to store parsed arguments
    """
    pass
