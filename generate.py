import sys
import copy
import random
from crossword import *

class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        newDomains = copy.deepcopy(self.domains)
        for var in self.crossword.variables:
            for word in self.domains[var]:
                if var.length != len(word):
                    newDomains[var].remove(word)
        self.domains = newDomains

    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        overlap = self.crossword.overlaps[x,y]
        domain = []
        for wordX in self.domains[x]:
            overlapWords = []
            for wordY in self.domains[y]:
                if wordX[overlap[0]] == wordY[overlap[1]]:
                    overlapWords.append(wordY)
            if len(overlapWords) != 0:
                domain.append(wordX)
        self.domains[x] = domain
        return len(domain) != len(self.domains[x])
        
    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        queue = []
        if arcs == None:
            for x in self.crossword.variables:
                for y in self.crossword.neighbors(x):
                    queue.append((x,y))
        else:
            for arc in arcs:
                queue.append(arc)

        while len(queue) != 0:
            temp = queue.pop(0)
            x, y = temp[0], temp[1]
            if self.revise(x, y):
                if len(self.domains[x]) == 0:
                    return False
                else:
                    for z in self.crossword.neighbors(x):
                        if z.i != y.i and z.j != y.j:
                            queue.append((x, z))
        return True

    def assignment_complete(self, assignment):
        """
        #Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        for var in self.crossword.variables:
            if var not in assignment:
                return False
        return True

    def consistent(self, assignment):
        """
        #Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        for var in assignment:
            if len(assignment.values()) != len(set(assignment.values())) or var.length != len(assignment[var]):
                return False

            for neighbor in self.crossword.neighbors(var):
                if assignment[neighbor] == None:
                    continue
                overlap = self.crossword.overlaps[var,neighbor]
                if overlap :
                    if (assignment[var][overlap[0]] != assignment[neighbor][overlap[1]]):
                        return False
        return True

    def order_domain_values(self, var, assignment):
        """
        #Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        unorderedValues = {}
        orderedValues = []
        for varWord in self.domains[var]:
            n = 0
            for neighbor in self.crossword.neighbors(var):
                if neighbor not in assignment.keys():
                    for neighborWord in self.domains[neighbor]:
                        overlap = self.crossword.overlaps[var, neighbor]
                        if varWord[overlap[0]] == neighborWord[overlap[1]]:
                            n += 1
            unorderedValues[varWord] = n

        for value in sorted(unorderedValues.items(), key=lambda item: item[1]):
            orderedValues.append(value[0])

        return orderedValues

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        untreatedVar = {}
        for var in self.crossword.variables:
            if var not in assignment.keys():
                untreatedVar[var] = len(self.domains[var])

        orderedUntreatedVarByMinValue = []
        for var in untreatedVar.keys():
            if untreatedVar[var] == min(untreatedVar.values()):
                orderedUntreatedVarByMinValue.append(var)
        if len(untreatedVar) == 1:
            return orderedUntreatedVarByMinValue[0]

        varDegree = {}
        for var in orderedUntreatedVarByMinValue:
            varDegree[var] = len(self.crossword.neighbors(var))

        orderedUntreatedVarByDegree = []
        for var in orderedUntreatedVarByMinValue:
            if varDegree[var] == min(varDegree.values()):
                orderedUntreatedVarByDegree.append(var)

        return random.choice(orderedUntreatedVarByDegree)

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment):
            if self.consistent(assignment):
                return assignment
            else:
                return None

        selectedVar = self.select_unassigned_variable(assignment)
        savedDomain = self.domains[selectedVar]
        for value in self.order_domain_values(selectedVar, assignment):
            newAssignment = assignment.copy()
            newAssignment[selectedVar] = value
            arcs = []
            for neighbor in self.crossword.neighbors(selectedVar):
                arcs.append((selectedVar, neighbor))
            self.ac3(arcs=arcs)
            result = self.backtrack(newAssignment)
            if result != None:
                return result

        self.domains[selectedVar] = savedDomain

def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
