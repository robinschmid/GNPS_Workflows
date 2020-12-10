# define the charge of common adduct parts
# neutral losses do not need to be added
CHARGE_DICT = dict(
    H=1, Li=1, Na=1, K=1, NH4=1,  # single
    Ca=2, Fe=2, Mg=2,  # double
    FA=-1, Fa=-1, Formate=-1, formate=-1, HCOO=-1, CHOO=-1, CH3COO=-1, C2H3OO=-1, H3C2OO=-1, C2H3O2=-1, Ac=-1, AC=-1,
    OAc=-1, HCO2=-1, CHO2=-1,
    Oac=-1, OFA=-1, OFa=-1, Ofa=-1, Cl=-1,
    Br=-1, I=-1, OH=-1,  # negative
    H2O=0, ACN=0, AcN=0, HFA=0, MeOH=0, EtOH=0, i=0, TFA=0,  # neutral
    # special
    Cat=1  # weird [M]+ radical
)

FORMULA_DICT = dict(
    FA="CHOO", Fa="CHOO", Formate="CHOO", formate="CHOO", HCOO="CHOO", C2H3OO="CH3COO", H3C2OO="CH3COO", C2H3O2="CH3COO",
    Ac="CH3COO", AC="CH3COO", OAc="CH3COO", Oac="CH3COO", OFA="CHOO", OFa="CHOO", Ofa="CHOO", TFA="CF3COOH",
    ACN="C2H3N", AcN="C2H3N", HFA="CHOOH", HAc="CH3COOH", MeOH="CH4O", EtOH="C2H6O"
)

UNKNOWN_ADDUCT_LIST = ["unk", "?", "??", "???", "unknown", "M+?", "M-?", "M"]
DEFAULT_UNKNOWN = "unknown"

class AdductPart(object):
    def __init__(self, sign, name, multiplier, replace_names_by_formulas=False):
        self.sign = sign
        self.name = name
        if replace_names_by_formulas:
            self.name = self.get_formula(default=name)
        self.input_name = name
        self.multiplier = int(1 if multiplier is None or len(str(multiplier)) <= 0 else multiplier)
        self.charge_calc = self.calculate_charge()
        self.replace_names_by_formulas = replace_names_by_formulas

    def __str__(self):
        return (self.sign +
                (str(self.multiplier) if self.multiplier > 1 else "") + self.name)

    def calculate_charge(self):
        """
        Uses a lookup dict to calculate the charge
        :return:
        """
        return CHARGE_DICT.get(self.name, 0) * self.multiplier * get_sign_multiplier(self.sign)

    def create(sign, name, replace_names_by_formulas=False):
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
        return AdductPart(sign, new_name, multiplier, replace_names_by_formulas)

    def get_formula(self, default=""):
        """
        Returns the formula found in FORMULA_DICT or default
        :param default:
        :return:
        """
        # TODO add test for formula (can name be parsed as formula?)
        if self.name in FORMULA_DICT:
            return FORMULA_DICT[self.name]
        else:
            return default

def get_sign_multiplier(sign):
    return (-1 if sign == "-" else 1)


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


def is_unknown(adduct):
    """
    True if adduct is a listed unknown adduct (e.g., "unknown", "M+?", "?")
    :param adduct:
    :return:
    """
    for unknown in UNKNOWN_ADDUCT_LIST:
        if unknown.lower() == adduct.lower():
            return True
    return False

def charge_from_str(charge, charge_sign):
    if len(str(charge_sign)) <= 0:
        return 0
    try:
        charge_abs = (int(charge) if len(str(charge).strip()) > 0 else 1)
        return charge_abs * get_sign_multiplier(charge_sign)
    except:
        return 0


def clean_adduct(adduct, add_brackets=True, add_missing_charge=True, replace_names_by_formulas=False,
                 return_charge_calc=False):
    """
    Harmonizes adducts.
    :param adduct:
    :param add_brackets: add [M+H]+ brackets that are removed during clean up (True or False)
    :param add_missing_charge: calculates missing charge and adds it to the string
    :param return_charge_calc: returns a tuple of (harmonized adduct, caclulated_charge)
    :return: M-all losses+all additions CHARGE
    """
    # keep ] for now to handle charge as M+Ca]2
    new_adduct = adduct.replace(" ", "").replace("(", "").replace(")", "").replace("[", "")

    # find charge at the end of the string
    charge = ""
    charge_sign = ""
    for i in reversed(range(len(new_adduct))):
        if new_adduct[i] == "+" or new_adduct[i] == "-":
            # handle ++ as 2+
            if charge_sign == new_adduct[i]:
                charge = str(("2" if len(charge) == 0 else (int(charge)+1)))
            else:
                charge_sign = new_adduct[i]
        elif new_adduct[i].isdigit():
            charge = new_adduct[i] + charge
        else:
            # only use charge if charge sign was detected - otherwise no charge was declared
            if len(charge_sign) <= 0:
                charge = ""
            # special case to handle M+Ca]2 -> missing sign, will remove charge and try to calculate from parts
            if new_adduct[i] == "]":
                new_adduct = new_adduct[0:i + 1]
            break

    # now remove ] after charge detection
    new_adduct = new_adduct.replace("]", "")

    # check if unknown adduct
    if is_unknown(new_adduct):
        result = DEFAULT_UNKNOWN + charge + charge_sign
        charge_int = charge_from_str(charge, charge_sign)
        return ((result, charge_int) if return_charge_calc else result)

    # find neutral losses and additions
    parts = new_adduct.split("+")
    positive_parts = []
    negative_parts = []
    for p in parts:
        sp = p.split("-")
        positive_parts.append(AdductPart.create("+", sp[0], replace_names_by_formulas))
        for n in sp[1:]:
            negative_parts.append(AdductPart.create("-", n, replace_names_by_formulas))
    # sort by name
    m_part = positive_parts[0]
    m_part.sign = ""  # remove sign before M
    positive_parts = positive_parts[1:]
    positive_parts = sorted(positive_parts, key=lambda part: part.name)
    negative_parts = sorted(negative_parts, key=lambda part: part.name)

    # handle multimers: M2 -> 2M
    temp_multiplier = ""
    for i in reversed(range(len(m_part.name))):
        if m_part.name[i].isdigit():
            temp_multiplier = m_part.name[i] + temp_multiplier
        else:
            if len(temp_multiplier) > 0:
                m_part.multiplier = int(temp_multiplier)
            m_part.name = m_part.name[0:i + 1]
            break

    # handle weird Cat = [M]+ notation
    m_str = (str(m_part) if m_part.name != "Cat" else ((str(m_part.multiplier) if m_part.multiplier > 1 else "") + "M"))
    # combine strings: [M - all neutral losses  + all additions ] CHARGE
    new_adduct = m_str + "".join(map(str, negative_parts)) + "".join(map(str, positive_parts))

    if add_brackets:
        new_adduct = "[" + new_adduct + "]"

    if add_missing_charge or return_charge_calc:
        calc_charge = sum(p.charge_calc for p in positive_parts) + sum(p.charge_calc for p in negative_parts)
        # special case: Cat instead of [M]+
        if m_part.name == "Cat":
            calc_charge = 1

    if len(charge) > 0 or len(charge_sign) > 0:
        new_adduct += charge + charge_sign
    elif add_missing_charge:
        # add missing charge
        if add_missing_charge:
            if abs(calc_charge) > 1:
                new_adduct += str(abs(calc_charge))
            new_adduct += ("-" if calc_charge < 0 else "+" if calc_charge > 0 else "")
    return ((new_adduct, calc_charge) if return_charge_calc else new_adduct)

def calc_adduct_charge(adduct):
    """
    Harmonizes the adduct and calculates the charge
    :param adduct: adduct string
    :return: charge as int
    """
    return clean_adduct(adduct, False, False, True)[1]