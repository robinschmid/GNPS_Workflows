
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
        if len(name) <= 0:
            return AdductPart(sign, "", 1, replace_names_by_formulas)

        multiplier = ""
        new_name = name
        for i in range(len(name)):
            if not name[i].isdigit():
                multiplier = name[0:i]
                new_name = name[i:]
                break

        # handle special case where multiplier is at the end:
        # M+H2 should be M+2H,  + keep NH4 same
        # 1 capital letter, n small letters, and number at the end
        if len(multiplier) <= 0 and name[-1].isdigit():
            capital_letters = 0
            for i in reversed(range(len(name))):
                if name[i].isdigit():
                    multiplier = name[i] + multiplier
                elif name[i].isupper():
                    capital_letters += 1
            if capital_letters == 1:  # found multiplier at the end
                new_name = name[0:len(name)-len(multiplier)]
            else:  # too many capital letters - no multiplier - is formula (e.g. NH4)
                multiplier = ""

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


# test the code
if __name__ == '__main__':

    list2 = "?	2M-2H+3Na	2M-2H+Na	2M-2H2O+H	2M-H	2M-H+2Na	2M-H+4i	2M-H+Na	2M-H2O+H	2M+Ca-H	2M+Ca]2	2M+H	2M+H+2i	2M+H+CH3CN	2M+K	2M+Na	2M+NH4	3M+Ca-H	3M+Ca]2	3M+H	3M+Na	3M+NH4	4M+Ca]2	5M+Ca]2	Cat	Cat-2H	Cat-C12H20O10	Cat-C3H9N	Cat-C6H10O5	Cat+H	M	M-2(H2O)+H	M-2H	M-2H-H2O	M-2H+3K	M-2H+3Na	M-2H2O+H	M-3H2O+H	M-CH3	M-H	M-H-2H2O	M-H-C10H12O3	M-H-C10H15SO6N3	M-H-C10H18O9	M-H-C10H20	M-H-C11H18O9	M-H-C12H20O10	M-H-C12H20O9	M-H-C14H25O11N	M-H-C15H35O4P	M-H-C18H12O6	M-H-C2H2O	M-H-C2H3ON	M-H-C2H4O	M-H-C2H4O2	M-H-C3H5NO2	M-H-C4H8O4	M-H-C5H6O4	M-H-C5H7NO2	M-H-C5H7O2N	M-H-C6H10O3N2	M-H-C6H10O4	M-H-C6H10O5	M-H-C6H11O5	M-H-C6H12O5	M-H-C6H12O6	M-H-C6H14O7	M-H-C6H7O3N	M-H-C6H9O5SO3H	M-H-C6H9O9P	M-H-C7H4O4	M-H-C9H10O4	M-H-C9H6O3	M-H-CH2O2	M-H-CH2O2S	M-H-CH3	M-H-CH4O	M-H-CO2	M-H-H2O	M-H-H2O-HCO2H	M-H-H2S	M-H-NH3	M-H-O3S	M-H]-	M-H+2i	M-H+2Na	M-H+CH3OH	M-H+HCOOH	M-H1	M-H2O	M-H2O-H	M-H2O+H	M-HAc	M-NH3+H	M+2H	M+2H]2	M+2H/2	M+2H+Na	M+3H	M+ACN+H	M+C2H3O2	M+Ca]2	M+CH3COO	M+CH3COOH-H	M+Cl	M+Cl+2i	M+FA-H	M+Fe	M+Formate	M+H	M+H-(CH3)2NH	M+H-2CH4	M+H-2H2O	M+H-3CH4	M+H-3H2O	M+H-4H2O	M+H-C10H12O4	M+H-C10H12O7	M+H-C10H14ClNO2	M+H-C10H14O6N2	M+H-C10H16	M+H-C10H16O13N5P3	M+H-C10H17F3O4	M+H-C10H17N3O6S	M+H-C10H9O2N	M+H-C11H11O2N	M+H-C11H12N2O3	M+H-C11H14O6	M+H-C11H14O6S	M+H-C11H16O7	M+H-C11H18O9	M+H-C11H20O10	M+H-C11H22O11	M+H-C12H14O5	M+H-C12H16O	M+H-C12H16O6	M+H-C12H20O10	M+H-C12H20O9	M+H-C12H22O10	M+H-C12H22O11	M+H-C12H24O11	M+H-C12H24O12	M+H-C12H26O13	M+H-C13H12O9	M+H-C13H14O9	M+H-C13H18O5	M+H-C13H21NO8	M+H-C13H25O3N	M+H-C14H15SO3N	M+H-C14H21N3O2S	M+H-C14H26O7	M+H-C15H16O7	M+H-C15H20O8	M+H-C16H15NO4	M+H-C16H25O9N	M+H-C16H28O14	M+H-C16H28O3	M+H-C16H30O15	M+H-C16H30O2	M+H-C16H32	M+H-C16H32O2	M+H-C17H30O15	M+H-C17H32O16	M+H-C18H30O13	M+H-C18H31ON	M+H-C18H32O2	M+H-C18H34O2	M+H-C19H32	M+H-C19H38	M+H-C19H38O4	M+H-C20H36O11	M+H-C20H36O12	M+H-C20H38O12	M+H-C20H38O13	M+H-C20H42O4NP	M+H-C24H44O-H2O	M+H-C26H48O18	M+H-C27H50O4	M+H-C2H10O5	M+H-C2H2O	M+H-C2H4	M+H-C2H4O	M+H-C2H4O2	M+H-C2H4OS	M+H-C2H5NO2	M+H-C2H5O2N	M+H-C2H6O	M+H-C2H6O2	M+H-C2H6O3	M+H-C2H6O4	M+H-C2H7N	M+H-C2H7NO	M+H-C2H7NO3	M+H-C2H7O3N	M+H-C2H7ON	M+H-C2H8FNO	M+H-C2H8NO4P	M+H-C2H8O2	M+H-C2H8O4	M+H-C2H8O4NP	M+H-C2H9ON	M+H-C3H10O2	M+H-C3H10O4	M+H-C3H12O3	M+H-C3H12O5	M+H-C3H14O6	M+H-C3H4N2	M+H-C3H4O	M+H-C3H5ClO	M+H-C3H6	M+H-C3H6O	M+H-C3H6O2	M+H-C3H7NO2	M+H-C3H7O3N	M+H-C3H8NO6P	M+H-C3H8O	M+H-C3H8O2	M+H-C3H8O3	M+H-C3H9ClO3	M+H-C3H9FO2	M+H-C3H9O6P	M+H-C4H10O	M+H-C4H10O2	M+H-C4H10O4S	M+H-C4H10O6	M+H-C4H12O2	M+H-C4H14O3	M+H-C4H4O2	M+H-C4H5O3N	M+H-C4H6	M+H-C4H6O3	M+H-C4H7O2N	M+H-C4H8	M+H-C4H8O2	M+H-C4H8O3	M+H-C4H8O4	M+H-C4H9NO2	M+H-C4H9NO3	M+H-C4H9ON	M+H-C5H10	M+H-C5H10O2	M+H-C5H10O4	M+H-C5H10O5	M+H-C5H11ON	M+H-C5H12O2	M+H-C5H13ON3	M+H-C5H14NO4P	M+H-C5H6O3	M+H-C5H6O4	M+H-C5H7ClN2O2S	M+H-C5H7O2N	M+H-C5H7O3N	M+H-C5H8	M+H-C5H8O	M+H-C5H8O2	M+H-C5H8O4	M+H-C5H9NO3	M+H-C5H9NO4+H2O	M+H-C5H9O7P	M+H-C5H9SO3N	M+H-C6H10O	M+H-C6H10O3	M+H-C6H10O4	M+H-C6H10O5	M+H-C6H10O7	M+H-C6H11NO	M+H-C6H11NO4	M+H-C6H12O	M+H-C6H12O2	M+H-C6H12O3	M+H-C6H12O4	M+H-C6H12O5	M+H-C6H12O6	M+H-C6H12O8	M+H-C6H13NO3	M+H-C6H14O	M+H-C6H14O2	M+H-C6H14O4	M+H-C6H14O7	M+H-C6H16O8	M+H-C6H17NO2	M+H-C6H4	M+H-C6H6INO2S	M+H-C6H6O2	M+H-C6H6O3	M+H-C6H8INO3S	M+H-C6H8O3N2	M+H-C6H8O6	M+H-C6H9NO2	M+H-C7H10ClNO3S	M+H-C7H11NO	M+H-C7H11NO2	M+H-C7H13NO2	M+H-C7H14	M+H-C7H14O	M+H-C7H16O2	M+H-C7H16O3	M+H-C7H4O2	M+H-C7H6O3	M+H-C7H6O5	M+H-C7H7IO2	M+H-C7H7NO2	M+H-C7H7SON	M+H-C7H8ClNO2S	M+H-C7H8N2O5	M+H-C7H8O3	M+H-C7H8O4	M+H-C7H9NO	M+H-C8H11ClN2O	M+H-C8H14O2	M+H-C8H14O3	M+H-C8H16O2	M+H-C8H16O3	M+H-C8H16O4	M+H-C8H18O	M+H-C8H18O2	M+H-C8H18O3	M+H-C8H9NO	M+H-C9H10O	M+H-C9H10O2	M+H-C9H10O5	M+H-C9H12O3	M+H-C9H14N2O2	M+H-C9H16	M+H-C9H16O4	M+H-C9H20O	M+H-C9H20O5	M+H-C9H7ClON2	M+H-CH2N2O2	M+H-CH2O	M+H-CH2O2	M+H-CH2O3	M+H-CH3	M+H-CH3N	M+H-CH3NH2	M+H-CH4	M+H-CH4O	M+H-CH4O2	M+H-CH4O3	M+H-CH4O4	M+H-CH4S	M+H-CH5N	M+H-CH5NO	M+H-CH6O2	M+H-CH6O3	M+H-CH6O4	M+H-CH8O3	M+H-CH8O4	M+H-CHNO	M+H-ClO2N	M+H-CO	M+H-CO2	M+H-H2O	M+H-H2O-NH3	M+H-H2O+2i	M+H-H2O2	M+H-H2O4S	M+H-H2OS2	M+H-H2SO4	M+H-H3FO	M+H-H3O4P	M+H-H4SO5	M+H-H5FO2	M+H-H6SO6	M+H-HF	M+H-N2	M+H-NH3	M+H-O2N	M+H-O2S	M+H-O3S	M+H-SO3	M+H+2i	M+H+4i	M+H+6i	M+H+CH3CN	M+H+CH3OH	M+H+H2O	M+H+K	M+H+Na	M+H+NH3+2i	M+H+NH4	M+HCO2	M+HCOO	M+K	M+K+H2O	M+Li	M+Na	M+Na-2H	M+Na-H2O	M+NH4	M+NH4-H2O	M+Oac	M+OAc	M+OH	M+TFA-H	M2+H	M2+Na	Unk"
    list2 = list2.split("	")

    for a in list2:
        harmonized = clean_adduct(a, True, True, True, True)
        harmonized_keep_names = clean_adduct(a, True, True, False, True)
        # print("{0}\t{1}\t{3}\t{2}".format(a, harmonized[0], str(harmonized[1]), harmonized_keep_names[0]))
        print("{0:14} --> {1:14} or {3:14} ({2})".format(a, harmonized[0], str(harmonized[1]), harmonized_keep_names[
            0]))