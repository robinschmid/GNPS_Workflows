# define the charge of common adduct parts
# neutral losses do not need to be added
CHARGE_DICT = dict(
    H=1, Li=1, Na=1, K=1,  # single
    Ca=2, Fe=2, Mg=2,  # double
    FA=-1, Fa=-1, Ac=-1, AC=-1, Cl=-1, Br=-1, I=-1,  # negative
    H2O=0, ACN=0, HFA=0, MeOH=0, EtOH=0  # neutral
)


class AdductPart(object):
    def __init__(self, sign, name, multiplier):
        self.sign = sign
        self.name = name
        self.multiplier = int(1 if multiplier is None or len(str(multiplier)) <= 0 else multiplier)
        self.charge_calc = self.calculate_charge()

    def __str__(self):
        return (self.sign +
                (str(self.multiplier) if self.multiplier > 1 else "") + self.name)

    def calculate_charge(self):
        """
        Uses a lookup dict to calculate the charge
        :return:
        """
        return CHARGE_DICT.get(self.name, 0) * self.multiplier * self.get_sign_multiplier()

    def get_sign_multiplier(self):
        return (-1 if self.sign == "-" else 1)

    def create(sign, name):
        """
        Creates an AdductPart from sign and name.
        :param sign: + or -
        :param name: any part of adduct name: H2O or 2H2O. Will split number and name
        :return:
        """
        multiplier = ""
        new_name = name
        for i in range(len(name)):
            if not name[i].isdigit():
                multiplier = name[0:i]
                new_name = name[i:]
                break
        return AdductPart(sign, new_name, multiplier)



def equal_adducts(a, b):
    """
    Checks if two adducts are equal. Uses clean_adduct to harmonize notation
    :param a:
    :param b:
    :return: True or False
    """
    if a is None or b is None or len(a)<=0 or len(b)<=0:
        return False

    ca = clean_adduct(a)
    cb = clean_adduct(b)

    if ca is None or cb is None or len(ca)<=0 or len(cb)<=0:
        return False

    if ca == cb:
        return True

    if ca[-1] == '-' and cb[-1] != '+':
        ca = ca[:-1]
        return ca == cb
    if ca[-1] == '+' and cb[-1] != '-':
        ca = ca[:-1]
        return ca == cb
    if cb[-1] == '-' and ca[-1] != '+':
        cb = cb[:-1]
        return ca == cb
    if cb[-1] == '+' and ca[-1] != '-':
        cb = cb[:-1]
        return ca == cb
    return False





def clean_adduct(adduct, add_brackets=True, add_missing_charge=True, return_charge_calc=False):
    """
    Harmonizes adducts.
    :param adduct:
    :param add_brackets: add [M+H]+ brackets that are removed during clean up (True or False)
    :param add_missing_charge: calculates missing charge and adds it to the string
    :param return_charge_calc: returns a tuple of (harmonized adduct, caclulated_charge)
    :return: M-all losses+all additions CHARGE
    """
    new_adduct = adduct
    new_adduct = new_adduct.replace("[", "")
    new_adduct = new_adduct.replace("]", "")
    new_adduct = new_adduct.replace(" ", "")

    # find charge at the end of the string
    charge = ""
    charge_sign = ""
    for i in reversed(range(len(new_adduct))):
        if new_adduct[i] == "+" or new_adduct[i] == "-":
            charge_sign = new_adduct[i]
        elif new_adduct[i].isdigit():
            charge = new_adduct[i] + charge
        else:
            new_adduct = new_adduct[0:i + 1]
            break

    # find neutral losses and additions
    parts = new_adduct.split("+")
    positive_parts = []
    negative_parts = []
    for p in parts:
        sp = p.split("-")
        positive_parts.append(AdductPart.create("+", sp[0]))
        for n in sp[1:]:
            negative_parts.append(AdductPart.create("-", n))
    # sort by name
    m_part = positive_parts[0]
    m_part.sign = ""  # remove sign before M
    positive_parts = positive_parts[1:]
    positive_parts = sorted(positive_parts, key=lambda part: part.name)
    negative_parts = sorted(negative_parts, key=lambda part: part.name)

    # combine strings: [M - all neutral losses  + all additions ] CHARGE
    new_adduct = str(m_part) + "".join(map(str, negative_parts)) + "".join(map(str, positive_parts))

    if add_brackets:
        new_adduct = "[" + new_adduct + "]"

    if add_missing_charge or return_charge_calc:
        calc_charge = sum(p.charge_calc for p in positive_parts) + sum(p.charge_calc for p in negative_parts)

    if len(charge) > 0 or len(charge_sign) > 0:
        new_adduct += charge + charge_sign
    elif add_missing_charge:
        # add missing charge
        if add_missing_charge:
            if abs(calc_charge) > 1:
                new_adduct += str(abs(calc_charge))
            new_adduct += ("-" if calc_charge < 0 else "+")
    return ((new_adduct, calc_charge) if return_charge_calc else new_adduct)

def calc_adduct_charge(adduct):
    """
    Harmonizes the adduct and calculates the charge
    :param adduct: adduct string
    :return: charge as int
    """
    return clean_adduct(adduct, False, False, True)[1]