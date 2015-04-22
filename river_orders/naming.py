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
        (r"Протока", "протока"),
        (r"рукав", "Рукав"),
        (r"(рукав|приток) р. ", ""),
        (r"([а-яА-Я-]+)\s+протока", r"протока \1"),
        (r"(.*)", r"протока \1"),
        (r"[В|в]{1}дхр(?!\.)", "вдхр."),
        (r'№\s*(\d+)', r'№\1'),
        (r'№(\d+)', r'№ \1'),
        (r"^([А-Я]{1}[а-яА-Я-]+)$", r'Ручей \1'),
        (r"^([А-Я]{1}[а-яА-Я-]+)$", r'Ключ \1'),
        (r"^([А-Я]{1}[а-яА-Я-]+)$", r'осушительный канал \1'),
        (r"([а-яА-Я-]+)\.([а-яА-Я-]+)", r'\1 . \2'),
        (r'ё', 'е'),
        (r'Ё', 'Е'),
        (r'Й', 'И'),
        (r'й', 'и')
    )
    _dash_capitalise = (
        r'(?=Кок)(Кок)(.*)$',
    )
    _abbreviations = (
        ('Бел.', ('Белый', 'Белая', 'Белое')),
        ('Красн.', ('Красный', 'Красная', 'Красное')),
        ('Прав.', ('Правый', 'Правая', 'Правое')),
        ('Лев.', ('Левый', 'Левая', 'Левое')),
        ('Бол.', ('Большой', 'Большая', 'Большое')),
    )
    _case_insensitive_replacements = (
    )

    def __init__(self):
        self.substrings = list(
            map(re.compile, self._substrings))
        self.replacements = list(
            map(lambda x: (re.compile(x[0]), x[1]), self._replacements))
        self.dash_capitalise = list(
            map(re.compile, self._dash_capitalise))

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
        titles = (name.title() for name in river.names)

        def _double_replacement(truncated, morphed, name):
            return name.replace(truncated, morphed), name.replace(morphed, truncated)
        abbrs = itertools.chain(
            *(_double_replacement(r[0], morphed, name) for name in river.names
              for r in self._abbreviations for morphed in r[1]))

        g = itertools.tee(itertools.chain(subs, repls, dcs, titles, abbrs))
        return set(itertools.chain(g[0], map(lambda x: x.strip(), g[1])))
