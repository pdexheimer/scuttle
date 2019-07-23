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

import sys
import logging


class DuplicateArgumentError(Exception):
    def __init__(self, arg_name, context):
        self.duplicate_argument = arg_name
        self.duplicate_context = context


class CommandLineOption:
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
                sys.exit(1)
        return values


class Namespace:
    pass


class GlobalNamespace(Namespace):
    def __init__(self, global_template):
        for opt in global_template.options:
            opt._set_defaults(self)


class CommandDescription:
    def __init__(self, verb):
        self.verb = verb
        self.sub_commands = []
        self.options = []
        self.arguments = []
        self._parameters = {}

    def add_subcommand(self, subcommand):
        if subcommand.verb in self._parameters.keys():
            raise DuplicateArgumentError(subcommand.verb, self.verb)
        self.sub_commands.append(subcommand)
        self._parameters[subcommand.verb] = subcommand

    def add_option(self, name, *args, **kwargs):
        option = CommandLineOption(name, *args, **kwargs)
        for arg in [name] + list(args):
            if arg in self._parameters:
                raise DuplicateArgumentError(arg, self.verb)
            self._parameters[arg] = option
        self.options.append(option)

    def add_argument(self, name):
        self.arguments.append(name)

    def parse(self, args, global_template, global_namespace, namespace=None):
        if namespace is None:
            namespace = Namespace()
        for opt in self.options:
            opt._set_defaults(namespace)
        next_argument = 0
        remaining_args = list(args)
        while len(remaining_args) > 0:
            arg = remaining_args[0]
            if global_template.is_global(arg):
                global_template.parse(remaining_args, global_namespace)
            else:
                if arg not in self._parameters.keys():
                    if next_argument >= len(self.arguments):
                        return (namespace, global_namespace, remaining_args)
                    else:
                        setattr(namespace, self.arguments[next_argument], arg)
                        remaining_args.pop(0)
                        next_argument += 1
                        continue
                parameter = self._parameters[arg]
                remaining_args.pop(0)
                if isinstance(parameter, CommandDescription):
                    namespace.subcommand = parameter.verb
                    return parameter.parse(remaining_args, global_template, global_namespace, namespace)
                elif isinstance(parameter, CommandLineOption):
                    arguments = remaining_args[:parameter.nargs]
                    del remaining_args[:parameter.nargs]
                    parameter.parse(arguments, namespace)
                else:
                    raise ValueError
        if next_argument < len(self.arguments):
            print(f'Missing {len(self.arguments)-next_argument} required arguments')
        return (namespace, global_namespace, remaining_args)


class CommandTemplate:
    def __init__(self, description, dispatch, validate=None):
        self.description = description
        self.name = self.description.verb
        self.dispatch = dispatch
        self.validate = validate if validate is not None else CommandTemplate.no_validate

    def no_validate(args):
        pass


class GlobalTemplate:
    def __init__(self, option_list, dispatch, validate=None):
        self.options = option_list
        self.dispatch = dispatch
        self.validate = validate if validate is not None else GlobalTemplate.no_validate
        self._parameters = {y: x for x in option_list for y in x.all_names}

    def is_global(self, arg):
        return arg in self._parameters.keys()

    def parse(self, args, namespace):
        while len(args) > 0:
            arg = args[0]
            if arg not in self._parameters.keys():
                return
            parameter = self._parameters[arg]
            args.pop(0)
            if isinstance(parameter, CommandLineOption):
                arguments = args[:parameter.nargs]
                del args[:parameter.nargs]
                parameter.parse(arguments, namespace)
            else:
                raise ValueError
        return

    def no_validate(args):
        pass


class Command:
    def __init__(self, args, dispatch, validate):
        self.args = args
        self.dispatch = dispatch
        self.validate = validate

    def validate_args(self):
        self.validate(self.args)

    def execute(self, *args, **kwargs):
        self.dispatch(self.args, *args, **kwargs)


def parse(template_list, global_template, argv=None):
    if argv is None:
        argv = sys.argv[1:]
    global_args = GlobalNamespace(global_template)
    lookup = {x.name: x for x in template_list}
    commands = []
    remaining_args = list(argv)
    while len(remaining_args) > 0:
        arg = remaining_args[0]
        if arg in lookup:
            remaining_args.pop(0)
            (parsed_args, global_args, remaining_args) = lookup[arg].description.parse(
                remaining_args,
                global_template,
                global_args
            )
            commands.append(Command(parsed_args, lookup[arg].dispatch, lookup[arg].validate))
        elif global_template.is_global(arg):
            global_template.parse(remaining_args, global_args)
        else:
            print(f'Unparsed arguments: {remaining_args}')
            break
    return (Command(global_args, global_template.dispatch, global_template.validate), commands)
