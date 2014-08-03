import unicodedata
from collections import Counter
from math import log
import re
from functools import wraps
from itertools import izip, takewhile


def cached_property(f):
    """ Property that will replace itself with a calculated value """
    name = '__' + f.__name__

    @wraps(f)
    def wrapper(self):
        if not hasattr(self, name):
            setattr(self, name, f(self))
        return getattr(self, name)
    return property(wrapper)


class PasswordStats(object):
    """ Password statistics """

    def __init__(self, password):
        self.password = unicode(password)

    #region Statistics

    @cached_property
    def alphabet(self):
        """ Get alphabet: set of used characters

        :rtype: set
        """
        return set(self.password)

    @cached_property
    def alphabet_cardinality(self):
        """ Get alphabet cardinality: alphabet length

        :rtype: int
        """
        return len(self.alphabet)

    @cached_property
    def char_categories_detailed(self):
        """ Character count per unicode category, detailed format.

        See: http://www.unicode.org/reports/tr44/#GC_Values_Table

        :returns: Counter( unicode-character-category: count )
        :rtype: collections.Counter
        """
        return Counter(map(unicodedata.category, self.password))

    @cached_property
    def char_categories(self):
        """ Character count per top-level category

        The following top-level categories are defined:

        - L: letter
        - M: Mark
        - N: Number
        - P: Punctuation
        - S: Symbol
        - Z: Separator
        - C: Other

        :return: Counter(unicode-character-category: count }
        :rtype: collections.Counter
        """
        c = Counter()
        for cat, n in self.char_categories_detailed.items():
            c[cat[0]] += n
        return c

    #endregion

    #region Counters

    @cached_property
    def length(self):
        """ Get password length

        :rtype: int
        """
        return len(self.password)

    @cached_property
    def letters(self):
        """ Count all letters

        :rtype: int
        """
        return self.char_categories['L']

    @cached_property
    def letters_uppercase(self):
        """ Count uppercase letters

        :rtype: int
        """
        return self.char_categories_detailed['Lu']

    @cached_property
    def letters_lowercase(self):
        """ Count lowercase letters

        :rtype: int
        """
        return self.char_categories_detailed['Ll']

    @cached_property
    def numbers(self):
        """ Count numbers

        :rtype: int
        """
        return self.char_categories['N']

    def count(self, *categories):
        """ Count characters of the specified classes only

        :param categories: Character categories to count
        :type categories: Iterable
        :rtype: int
        """
        return sum(map(lambda (cat, n): int(cat in categories)*n, self.char_categories.items()))

    def count_except(self, *categories):
        """ Count characters of all classes except the specified ones

        :param categories: Character categories to exclude from count
        :type categories: Iterable
        :rtype: int
        """
        return sum(map(lambda (cat, n): int(cat not in categories) * n, self.char_categories.items()))

    @cached_property
    def special_characters(self):
        """ Count special characters

        Special characters is everything that's not a letter or a number

        :rtype: int
        """
        return self.count_except('L', 'N')

    #region Security

    @cached_property
    def combinations(self):
        """ The number of possible combinations with the current alphabet

        :rtype: long
        """
        return self.alphabet_cardinality ** self.length

    @cached_property
    def entropy_bits(self):
        """ Get information entropy bits: log2 of the number of possible passwords

        https://en.wikipedia.org/wiki/Password_strength

        :rtype: float
        """
        return self.length * log(self.alphabet_cardinality, 2)

    def strength(self):
        """ Get password strength as a number normalized to range 0..1

        :rtype: float
        """


    #endregion

    #region Detectors

    _repeated_patterns_rex = re.compile(r'((.+?)\2+)', re.UNICODE | re.DOTALL | re.IGNORECASE)

    @cached_property
    def repeated_patterns_length(self):
        """ Detect and return the length of repeated patterns.

        You will probably be comparing it with the length of the password itself and ban if it's longer than 10%

        :rtype: int
        """
        length = 0
        for substring, pattern in self._repeated_patterns_rex.findall(self.password):
            length += len(substring)
        return length

    _sequences = (
        'abcdefghijklmnopqrstuvwxyz'  # Alphabet
        'qwertyuiopasdfghjklzxcvbnm'  # Keyboard
        '~!@#$%^&*()_+-='  # Keyboard special, top row
        '01234567890'  # Numbers
    )
    _sequences = _sequences + _sequences[::-1]  # reversed

    @cached_property
    def sequences_length(self):
        """ Detect and return the length of used sequences:

        - Alphabet letters: abcd...
        - Keyboard letters: qwerty, etc
        - Keyboard special characters in the top row: ~!@#$%^&*()_+
        - Numbers: 0123456

        :rtype: int
        """
        # FIXME: Optimize this. I'm sure there is a better way!...
        sequences_length = 0

        # Iterate through the string, with manual variable (to allow skips)
        i = 0
        while i < len(self.password):
            # Slice (since we use it often)
            password = self.password[i:]

            # Iterate over sequences to find longest common prefix
            j = -1
            common_length = 1
            while True:
                # Detect the first match with the current character
                # A character may appear multiple times
                j = self._sequences.find(password[0], j+1)
                if j == -1:
                    break

                # Find the longest common prefix
                common_here = ''
                for a, b in izip(password, self._sequences[j:]):
                    if a != b: break
                    else: common_here += a

                # It it's longer than previous discoveries -- store it
                common_length = max(common_length, len(common_here))

            # Repeated sequence?
            if common_length > 1:
                sequences_length += common_length

            # Next: skip to the end of the detected sequence
            i += common_length

        return sequences_length



    #endregion