"""
ChemCalc Lab Assistant
Author: Braden Price (bradenp@udel.edu)

A Drafter web app that helps chemistry students find the limiting
reactant, theoretical yield, and percent yield of a reaction, and keeps
a history log of their results.
"""
from dataclasses import dataclass
from drafter import *


# Average atomic masses in g/mol for common elements (a global constant)
# used AI (found using Chemistry 2e (OpenStax)
ATOMIC_MASSES = {
    "H": 1.008, "He": 4.003, "Li": 6.94, "Be": 9.012, "B": 10.81,
    "C": 12.011, "N": 14.007, "O": 15.999, "F": 18.998, "Ne": 20.180,
    "Na": 22.990, "Mg": 24.305, "Al": 26.982, "Si": 28.085, "P": 30.974,
    "S": 32.06, "Cl": 35.45, "Ar": 39.948, "K": 39.098, "Ca": 40.078,
    "Fe": 55.845, "Cu": 63.546, "Zn": 65.38, "Br": 79.904, "Ag": 107.87,
    "I": 126.90, "Ba": 137.33, "Au": 196.97, "Pb": 207.2
}

#One saved lab record.
@dataclass
class ChemicalReaction:
    equation: str
    limiting_reactant: str
    target_product: str
    theoretical_yield_grams: float
    percent_yield: float

#Everything the website needs to remember between pages.
@dataclass
class State:
    active_equation: str
    total_calculations_run: int
    saved_reactions: list[ChemicalReaction]
    message: str

#++++
#HELPER FUNCTIONS
#++++
def is_number(text: str) -> bool:
    """Return True if text is a positive decimal number like 12 or 3.5."""
    text = text.strip()
    if text == "" or text == ".":
        return False
    dot_count = 0
    for character in text:
        if character == ".":
            dot_count = dot_count + 1
        elif not character.isdigit():
            return False
    return dot_count <= 1


def format_number(number: float) -> str:
    """Round a number to 3 decimal places and turn it into a string."""
    return str(round(number, 3))


def read_digits(text: str, start: int) -> str:
    """Return the run of digit characters in text beginning at start."""
    digits = ""
    index = start
    while index < len(text) and text[index].isdigit():
        digits = digits + text[index]
        index = index + 1
    return digits


def molar_mass(formula: str) -> float:
    """
    Return the molar mass (g/mol) of a formula like "H2O".
    Returns 0.0 if the formula has an unknown element or bad character.
    """
    total = 0.0
    index = 0
    while index < len(formula):
        if not formula[index].isupper():
            return 0.0
        symbol = formula[index]
        index = index + 1
        if index < len(formula) and formula[index].islower():
            symbol = symbol + formula[index]
            index = index + 1
        if symbol not in ATOMIC_MASSES:
            return 0.0
        digits = read_digits(formula, index)
        index = index + len(digits)
        count = 1
        if digits != "":
            count = int(digits)
        total = total + ATOMIC_MASSES[symbol] * count
    return total


def parse_side(side: str) -> list:
    """
    Turn one side of an equation ("2H2 + O2") into a list of
    [coefficient, formula] pairs. Returns [] if any formula is invalid.
    """
    species = []
    for term in side.split("+"):
        term = term.strip()
        digits = read_digits(term, 0)
        coefficient = 1
        if digits != "":
            coefficient = int(digits)
        formula = term[len(digits):]
        if molar_mass(formula) == 0.0:
            return []
        species.append([coefficient, formula])
    return species


def parse_equation(equation: str) -> list:
    """
    Turn "2H2 + O2 -> 2H2O" into [reactants, products], where each is a
    list of [coefficient, formula] pairs. Returns [] if invalid.
    """
    sides = equation.split("->")
    if len(sides) != 2:
        return []
    reactants = parse_side(sides[0])
    products = parse_side(sides[1])
    if reactants == [] or products == []:
        return []
    return [reactants, products]


def parse_mass_list(text: str) -> list[float]:
    """Turn "10, 5.5" into [10.0, 5.5]. Returns [] if any piece is bad."""
    masses = []
    for piece in text.split(","):
        if not is_number(piece):
            return []
        masses.append(float(piece))
    return masses


def find_limiting_index(reactants: list, masses: list[float]) -> int:
    """Index of the reactant with the smallest moles / coefficient."""
    best_index = 0
    for index in range(len(reactants)):
        ratio = masses[index] / molar_mass(reactants[index][1]) / \
            reactants[index][0]
        best_ratio = masses[best_index] / \
            molar_mass(reactants[best_index][1]) / reactants[best_index][0]
        if ratio < best_ratio:
            best_index = index
    return best_index


def theoretical_yield(reactants: list, masses: list[float],
                      products: list, target: str) -> float:
    """Grams of the target product made if the limiting reactant runs out."""
    limit = find_limiting_index(reactants, masses)
    reaction_moles = masses[limit] / molar_mass(reactants[limit][1]) / \
        reactants[limit][0]
    for pair in products:
        if pair[1] == target:
            return reaction_moles * pair[0] * molar_mass(target)
    return 0.0


def percent_yield(actual: float, theoretical: float) -> float:
    """Return actual / theoretical * 100, or 0.0 if theoretical is 0."""
    if theoretical <= 0:
        return 0.0
    return actual / theoretical * 100


def average_percent_yield(reactions: list[ChemicalReaction]) -> float:
    """Average percent yield of all saved reactions (0.0 if none)."""
    if len(reactions) == 0:
        return 0.0
    total = 0.0
    for reaction in reactions:
        total = total + reaction.percent_yield
    return total / len(reactions)


def show_message(state: State) -> list:
    """Return the current message (if any) as page content, then clear it."""
    if state.message == "":
        return []
    text = state.message
    state.message = ""
    return [text]


# ++++
# Routes (given by AI)
# ++++

@route
def index(state: State) -> Page:
    """The home page with links to each tool."""
    return Page(state, [
        Header("Chemistry Lab Assistant"),
        "Calculations run: " + str(state.total_calculations_run),
        Button("Limiting Reactant & Yield", stoichiometry_input),
        Button("Percent Yield Calculator", yield_calculator),
        Button("History Log", history_log)
    ])


@route
def stoichiometry_input(state: State) -> Page:
    """Step 1: the user types a balanced equation."""
    return Page(state, show_message(state) + [
        Header("Step 1: Equation"),
        "Enter a balanced equation, e.g. 2H2 + O2 -> 2H2O",
        TextBox("equation", state.active_equation),
        Button("Next", load_equation),
        Button("Home", index)
    ])


@route
def load_equation(state: State, equation: str) -> Page:
    """Step 2: checks the equation, then asks for masses and a product."""
    state.active_equation = equation.strip()
    parsed = parse_equation(state.active_equation)
    if parsed == []:
        state.message = "Could not read that equation. Try 2H2 + O2 -> 2H2O"
        return stoichiometry_input(state)
    reactant_names = []
    for pair in parsed[0]:
        reactant_names.append(pair[1])
    product_names = []
    for pair in parsed[1]:
        product_names.append(pair[1])
    return Page(state, show_message(state) + [
        Header("Step 2: Amounts"),
        "Equation: " + state.active_equation,
        "Grams of each reactant, in order (" + ", ".join(reactant_names) +
        "), separated by commas:",
        TextBox("reactant_masses", ""),
        "Product:",
        SelectBox("target_product", product_names, product_names[0]),
        "Actual grams of product collected:",
        TextBox("actual_grams", ""),
        Button("Calculate", stoichiometry_results),
        Button("Back", stoichiometry_input)
    ])


@route
def stoichiometry_results(state: State, reactant_masses: str,
                          target_product: str, actual_grams: str) -> Page:
    """Calculates the results, saves them to the log, and shows them."""
    parsed = parse_equation(state.active_equation)
    masses = parse_mass_list(reactant_masses)
    if len(masses) != len(parsed[0]) or not is_number(actual_grams):
        state.message = "Enter one mass per reactant and a number " + \
            "for the actual yield."
        return load_equation(state, state.active_equation)
    limiting = parsed[0][find_limiting_index(parsed[0], masses)][1]
    theoretical = theoretical_yield(parsed[0], masses, parsed[1],
                                    target_product)
    result = percent_yield(float(actual_grams), theoretical)
    state.saved_reactions.append(ChemicalReaction(
        state.active_equation, limiting, target_product, theoretical, result))
    state.total_calculations_run = state.total_calculations_run + 1
    return Page(state, [
        Header("Results"),
        "Limiting reactant: " + limiting,
        "Theoretical yield of " + target_product + ": " +
        format_number(theoretical) + " g",
        "Percent yield: " + format_number(result) + " %",
        Button("History Log", history_log),
        Button("Home", index)
    ])


@route
def yield_calculator(state: State) -> Page:
    """Quick percent yield tool when the theoretical yield is known."""
    return Page(state, show_message(state) + [
        Header("Percent Yield Calculator"),
        "Theoretical yield (g):",
        TextBox("theoretical_grams", ""),
        "Actual yield (g):",
        TextBox("actual_grams", ""),
        Button("Calculate", yield_results),
        Button("Home", index)
    ])


@route
def yield_results(state: State, theoretical_grams: str,
                  actual_grams: str) -> Page:
    """Shows the percent yield for the two numbers given."""
    if not is_number(theoretical_grams) or not is_number(actual_grams) \
            or float(theoretical_grams) <= 0:
        state.message = "Enter two numbers; theoretical must be above 0."
        return yield_calculator(state)
    state.total_calculations_run = state.total_calculations_run + 1
    result = percent_yield(float(actual_grams), float(theoretical_grams))
    return Page(state, [
        Header("Yield Result"),
        "Percent yield: " + format_number(result) + " %",
        Button("Try Again", yield_calculator),
        Button("Home", index)
    ])


@route
def history_log(state: State) -> Page:
    """Shows a table of every saved result and the average yield."""
    rows = []
    for reaction in state.saved_reactions:
        rows.append([reaction.equation, reaction.limiting_reactant,
                     format_number(reaction.theoretical_yield_grams) + " g",
                     format_number(reaction.percent_yield) + " %"])
    if rows == []:
        return Page(state, [Header("History Log"), "No results saved yet.",
                            Button("Home", index)])
    return Page(state, [
        Header("History Log"),
        Table(rows, header=["Equation", "Limiting", "Theoretical",
                            "Yield"]),
        "Average percent yield: " +
        format_number(average_percent_yield(state.saved_reactions)) + " %",
        Button("Home", index)
    ])


# ++++
# Unit tests
# ++++

def make_test_state() -> State:
    """A fresh State used by the tests below."""
    return State("2H2 + O2 -> 2H2O", 0, [], "")


# Helper function tests
assert_equal(is_number("12.5"), True)
assert_equal(is_number("abc"), False)
assert_equal(molar_mass("H2O"), 18.015, precision=3)
assert_equal(molar_mass("Xy"), 0.0)
assert_equal(parse_equation("2H2 + O2 -> 2H2O"),
             [[[2, "H2"], [1, "O2"]], [[2, "H2O"]]])
assert_equal(parse_equation("no arrow"), [])
assert_equal(parse_mass_list("10, 5.5"), [10.0, 5.5])
assert_equal(find_limiting_index([[2, "H2"], [1, "O2"]], [4.0, 16.0]), 1)
assert_equal(percent_yield(9.0, 10.0), 90.0)
assert_equal(percent_yield(9.0, 0.0), 0.0)
assert_equal(average_percent_yield([
    ChemicalReaction("A -> B", "A", "B", 1.0, 80.0),
    ChemicalReaction("A -> B", "A", "B", 1.0, 90.0)]), 85.0)

# Route tests (given by AI)
assert_equal(index(make_test_state()).state.total_calculations_run, 0)
assert_equal(stoichiometry_input(make_test_state()).state.active_equation,
             "2H2 + O2 -> 2H2O")
assert_equal(load_equation(make_test_state(), "CH4 + 2O2 -> CO2 + 2H2O")
             .state.active_equation, "CH4 + 2O2 -> CO2 + 2H2O")
test_results = stoichiometry_results(make_test_state(), "4, 16", "H2O",
                                     "15")
assert_equal(test_results.state.total_calculations_run, 1)
assert_equal(test_results.state.saved_reactions[0].limiting_reactant, "O2")
assert_equal(test_results.state.saved_reactions[0].theoretical_yield_grams,
             18.015, precision=2)
assert_equal(yield_calculator(make_test_state()).state.message, "")
assert_equal(yield_results(make_test_state(), "10", "9")
             .state.total_calculations_run, 1)
assert_equal(yield_results(make_test_state(), "0", "9")
             .state.total_calculations_run, 0)
assert_equal(history_log(make_test_state()).state.saved_reactions, [])


# ++++
# Start the website
# ++++

set_site_information(
    author="Braden Price",
    description="Chem Lab Assistant: finds the limiting reactant, "
                "theoretical yield, and percent yield for lab reactions.",
    sources=["Chemistry 2e (OpenStax), Chapter 4",
             "Drafter documentation: https://drafter-edu.github.io/drafter/"],
    planning=["Braden_Price_-_CS1_Final_Project_0__Pick_a_Problem.docx",
              "bradenp_udel_edu_-_CS1_Final_Project_1__Design__1_.docx"],
    links=["https://github.com/bradenp-236/chemistry-helper/"]
)
hide_debug_information()
start_server(State("", 0, [], ""))
