# third party software customized by goodcrypto

from syr.surlex.grammar import Parser, RegexScribe, get_all_nodes, MacroTagNode
from syr.surlex.macros import MacroRegistry, DefaultMacroRegistry
import re

class Surlex(object):
    def __init__(self, surlex, macro_registry=DefaultMacroRegistry()):
        self.translated = False
        self.surlex = surlex
        self.macro_registry = macro_registry

    def translate(self):
        if not self.translated:
            self.parser = Parser(self.surlex)
            self.node_list = self.parser.get_node_list()
            self.scribe = RegexScribe(
                self.node_list,
                self.macro_registry,
            )
            self._regex = self.scribe.translate()
            self._compiled_regex = re.compile(self._regex)
            
            self._macros = {}
            for node in get_all_nodes(self.node_list):
                if isinstance(node, MacroTagNode):
                    self._macros[node.name] = node.macro
                    
            self.translated = True
        return self._regex

    @property
    def groupmacros(self):
        if not self.translated:
            self.translate()
        return self._macros

    @property
    def regex(self):
        if not self.translated:
            self.translate()
        return self._regex

    @property
    def compiled_regex(self):
        if not self.translated:
            self.translate()
        return self._compiled_regex

    def match(self, subject):
        ''' Like re.match, except returns a dict if matched tags.'''
        
        m = self.compiled_regex.match(subject)
        if m:
            d = m.groupdict()
            if d:
                result = d
            else:
                result = True
        else:
            result = None
        return result
        
    def __unicode__(self):
        return self.surlex

# This allows "surlex.register_macro" to register to the default registry
register_macro = DefaultMacroRegistry.register

def surlex_to_regex(surlex):
    return Surlex(surlex).regex

def parsed_surlex_object(surlex):
    object = Surlex(surlex)
    object.translate()
    return object

def match(surlex, subject):
    return Surlex(surlex).match(subject)
