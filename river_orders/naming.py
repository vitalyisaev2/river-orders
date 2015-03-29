#! -*- coding: utf8 -*-
import itertools
import re


class NameSuggestion(object):
    """
    A collection of suggestions in the form of regular expressions
    that help to handle most common typos automatically
    """
    _substrings = (
        r"^[Пп]{1}ротока\s+р.\s+([а-яА-Я-]+)$",
        r"^([а-яА-Я-]+)\s*№\s*\d+$",
        r"^(оз.\s+[а-яА-Я-]+)\s+\(зал.\s+[а-яА-Я-]+\)$",
        r"^(оз.\s+[а-яА-Я-]+)\s+\([а-яА-Я-]+\s+залив\)$",
        r"^кл.\s+(.*)$"
    )
    _replacements = (
        (r"\.", ". "),
        (r"протока", "Протока"),
        (r"рукав", "Рукав"),
        (r"[В|в]{1}дхр(?!\.)", "вдхр."),
        (r'№\s*(\d+)', r'№\1'),
        (r"^([А-Я]{1}[а-яА-Я-]+)$", r'Ручей \1'),
        (r"^([А-Я]{1}[а-яА-Я-]+)$", r'Ключ \1'),
    )
    _dash_capitalise = (
        r'(?=Кок)(Кок)(.*)$',
    )
    _abbreviations = (
        ('Бел.', ('Белый', 'Белая', 'Белое')),
        ('Прав.', ('Правый', 'Правая', 'Правое')),
    )

    def __init__(self):
        self.substrings = list(
            map(re.compile, self._substrings))
        self.replacements = list(
            map(lambda x: (re.compile(x[0]), x[1]), self._replacements))
        self.dash_capitalise = list(
            map(re.compile, self._dash_capitalise))
        self.abbreviations = list(
            map(lambda x: (re.compile(x[0]), x[1]), self._abbreviations))

    def suggest(self, river):
        """
        provides the set of unique suggested names, according to the list of
        regular expressions
        """
        subs = (m.groups()[0] for name in river.names
                for m in map(lambda x: x.match(name), self.substrings) if m)
        repls = (r[0].sub(r[1], name) for name in river.names
                 for r in self.replacements)
        dcs = ("-".join(map(lambda x: x.title(), m.groups()))
                for m in (dc.match(name)
                            for name in river.names
                            for dc in self.dash_capitalise
                    ) if m)
        abbrs = (r[0].sub(form, name) for name in river.names for r in self.abbreviations for form in r[1])
        #abbrs = itertools.chain((form.sub([r[0], name), r[0].sub(form, name)) for name in river.names for form in r[1] for r in self.abbreviations)
        #def _double_replacement(truncated, morphed, name):
            #return truncated.replace(morphed, name), morphed.replace(truncated, name)
        #abbrs = itertools.chain(*(_double_replacement(r[0], morphed, name) for name in river.names for r in self._abbreviations for morphed in r[1]))
        g = itertools.tee(itertools.chain(subs, repls, dcs, abbrs))
        return set(itertools.chain(g[0], map(lambda x: x.strip(), g[1])))
