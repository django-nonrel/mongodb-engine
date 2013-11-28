import re


class BaseTokenizer(object):
    """
    Really simple tokenizer.
    """

    @staticmethod
    def tokenize(text):
        """
        Splits text into a list of words removing any symbol and
        converts it into lowercase.
        """
        tokens = []
        text = text.lower()
        for dot_item in BaseTokenizer.regex_split('\.(?=[a-zA-Z\s])', text):
            for comman_item in BaseTokenizer.regex_split(',(?=[a-zA-Z\s])',
                                                         dot_item):
                for item in comman_item.split(' '):
                    item = BaseTokenizer.tokenize_item(item)
                    if item:
                        tokens.append(item)
        return tokens

    @staticmethod
    def regex_split(regex, text):
        for item in re.split(regex, text, re.I):
            yield item

    @staticmethod
    def tokenize_item(item):
        """
        If it is an int/float it returns the item (there's no need to
        remove , or .).
        """
        item = item.strip()
        try:
            float(item)
            return item
        except ValueError:
            pass

        # This will keep underscores.
        return re.sub(r'[^\w]', '', item)
