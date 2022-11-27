import unicodedata


def antimakkcen(slovo):  # it just works
    normalized = unicodedata.normalize('NFD', slovo)
    slovo2 = u"".join([c for c in normalized if not unicodedata.combining(c)])
    return slovo2
