import hashlib
import re
import networkx as nx
import yaml

"""
Family is kept as a "directed multigraph" with Persons as
nodes.  Nodes can have more than one directed edge between
them.  Edges have a relation_type attribute that takes one
of the values "mother", "father", "spouse"

Persons have the attributes "gender" and "other" to be
filled with anything else useful to the person.
"""

class GenderError(Exception):
  pass

class GenealogicalError(Exception):
  pass

class PersonExistsError(Exception):
  pass


class Person(object):
  """
  Persons are uniquely identified by their name string.
  """
  def __init__(self, name, gender):
    self.name = name
    self.gender = gender

  # Only care about the name
  def __eq__(self, other):
    # If `other` doesn't even have a name, then no chance.
    if not hasattr(other, 'name'):
      return False
    return self.name == other.name

  def __ne__(self, other):
    # If `other` doesn't even have a name, they're guaranteed
    # do be different.
    if not hasattr(other, 'name'):
      return True
    return (self.name != other.name)

  # Really, only care about the name.  Persons with
  # different genders end up with the same hash if
  # they have the same name.
  def __hash__(self):
    return hash(self.name)

  def __str__(self):
    return self.name

  def __repr__(self):
    return "{} ({})".format(self.name, self.gender)

  def add_children(self, children):

    # Do nothing if any of the children are already present
    for child in children:
      if child in self.children:
        raise PersonExistsError(
            "{0} already a child of {1}".format(child, self)
        )

    for child in children:
      self.children.append(child)

  def add_child(self, child):
    self.add_children([child])

  def add_spouses(self, spouses):

    # Do nothing if any of the spouses are already present
    for spouse in spouses:
      if spouse in self.spouses:
        raise PersonExistsError(
            "{0} already a spouse of {1}".format(spouse, self)
        )

    for spouse in spouses:
      self.spouses.append(spouse)



class Family(object):
  """
  Family is kept as a "directed multigraph" with Persons as
  nodes.  Nodes can have more than one directed edge between
  them.  Edges have a relation_type attribute that takes one
  of the values "mother", "father", "spouse"

  Represent a family as a collection of Persons each with a
  unique .name property and connections between them.
  """
  def __init__(self, persons=None):
    # Full directed multipgraph of Persons with mother, father,
    # and spouse as all the relation_type's.
    self.graph = nx.MultiDiGraph()
    if persons == None:
      self.graph.add_nodes_from([])
    else:
      self.graph.add_nodes_from(persons)

    # Interesting data about individuals is kept in the
    # other_data dict, keyed by Persons.
    self.other_data = {}

  def __eq__(self, other):
    return (
      self.graph.nodes() == other.graph.nodes() and \
      self.graph.edges(data=True) == other.graph.edges(data=True)
    )

  def __ne__(self, other):
    return self != other

  def add_person(self, person):
    self.graph.add_node(person)

  def persons(self):
    return self.graph.nodes()

  def names(self):
    return [person.name for person in self.persons()]

  def add_child(self, parent, child):
    # Does nothing if `parent` already present
    self.graph.add_node(parent)
    relation_type = None
    if parent.gender == "male":
      relation_type = "father"
    elif parent.gender == "female":
      relation_type = "mother"
    else:
      raise GenderError("Without a gender on {}, can't tell"
          " whether she should be added "
          "as a mother or father.".format(parent))

    self.graph.add_edge(parent, child,
        relation_type=relation_type)

  def add_children(self, parent, children):
    for child in children:
      self.add_child(parent, child)

  def add_spouse(self, person, spouse):
    # Does nothing if `parent` already present
    self.graph.add_node(person)
    self.graph.add_edge(person, spouse, relation_type="spouse")

  def add_spouses(self, person, spouses):
    for spouse in spouses:
      self.add_spouse(person, spouse)

  def add_full_sibling(self, person, sibling):
    if person not in self.persons():
      raise PersonExistsError(
          "{} isn't in the family yet.".format(person))
    # Does nothing if `sibling` already present
    self.graph.add_node(sibling)

    # Add either parent if they don't exist
    if not self.father(person):
      self.add_father(person,
          Person(name=self.new_anonymous_name(), gender="male"))
    if not self.mother(person):
      self.add_mother(person,
          Person(name=self.new_anonymous_name(), gender="female"))

    self.graph.add_edge(self.father(person), sibling,
        relation_type="father")
    self.graph.add_edge(self.mother(person), sibling,
        relation_type="mother")


  def new_anonymous_name(self):
    """
    Collect all names of the form '????...'
    and return a new string of ?'s one longer than the
    longest
    """
    anon_lengths = [
      len(anon)
      for anon
      in self.names()
      if re.match('^\?+$', anon)
    ]
    if anon_lengths == []:
      longest = 0
    else:
      longest = max(anon_lengths)
    return '?' * (longest + 1)

  def add_mother(self, child, mother):

    # Error on already existing mother
    if self.mother(child) != None:
      raise GenealogicalError(
          "{0} already has a mother ({1})".format(child,
              self.mother(child)))

    # Error on mother and child the same
    if child == mother:
      raise GenealogicalError(
          "{0} can't mother herself".format(child))

    # Error on non-female mother
    if mother.gender != "female":
      raise GenderError("{0} isn't female, so can't " \
          "be a mother.".format(mother))

    # If already a mother of someone else, add to children
    # list
    mom_found = False
    for cur_mom in self.mothers():
      if cur_mom == mother:
        mom_found = True
        if child not in self.children(cur_mom):
          self.add_child(cur_mom, child)

    # Otherwise, add the mother and add the child
    if not mom_found:
      self.add_person(mother)
      self.add_child(mother, child)

  def add_father(self, child, father):

    # Error on already existing father
    if self.father(child) != None:
      raise GenealogicalError(
          "{0} already has a father ({1})".format(child,
              self.father(child)))

    # Error on father and child the same
    if child == father:
      raise GenealogicalError(
          "{0} can't father himself".format(child))

    # Error on non-male father
    if father.gender != "male":
      raise GenderError("{0} isn't male, so can't " \
          "be a father.".format(father))

    # If already a father of someone else, add to children
    # list
    dad_found = False
    for cur_dad in self.fathers():
      if cur_dad == father:
        dad_found = True
        if child not in self.children(cur_dad):
          self.add_child(cur_dad, child)

    # Otherwise, add the father and add the child
    if not dad_found:
      self.add_person(father)
      self.add_child(father, child)


  def children(self, parent):
    if parent not in self.persons():
      raise PersonExistsError(
          "{} isn't in the family yet.".format(parent))

    return [
      edge[1]
      for edge in self.graph.edges(data=True)
      if (edge[2]['relation_type'] == "father" or \
          edge[2]['relation_type'] == "mother") and \
         edge[0] == parent
    ]

  def fathers(self):
    return set([
        edge[0]
        for edge in self.graph.edges(data=True)
        if edge[2]['relation_type'] == "father"
    ])
  def mothers(self):
    return set([
        edge[0]
        for edge in self.graph.edges(data=True)
        if edge[2]['relation_type'] == "mother"
    ])
  def spouses(self):
    return set([
        edge[0]
        for edge in self.graph.edges(data=True)
        if edge[2]['relation_type'] == "spouse"
    ])
  def father(self, person):
    for edge in self.graph.edges(data=True):
      if edge[2]['relation_type'] == "father" and \
          edge[1] == person:
        return edge[0]
    return None
  def mother(self, person):
    for edge in self.graph.edges(data=True):
      if edge[2]['relation_type'] == "mother" and \
          edge[1] == person:
        return edge[0]
    return None
  def all_spouses(self, person):
    cur_spouses = []
    for edge in self.graph.edges(data=True):
      if edge[2]['relation_type'] == "spouse" and \
        edge[0] == person:
          cur_spouses.append(edge[1])
    return cur_spouses
  def persons(self):
    return self.graph.nodes()


def name_to_uid(name):
  """Give a unique id to any name"""
  return "personhash" + hashlib.md5(name).hexdigest()


def split_biglist(biglist):
  """
  Take `biglist` as would be returned from a .yaml file
  and return corresponding lists

      (fathers, mothers, spouses)

  e.g. `biglist` like

      biglist = [                                  \
        {'father': {'a': ['b', 'c'], 'd': ['e']}}, \
        {'mother': {'f': ['g', 'h'], 'i': ['j']}}, \
        {'spouse': {'k': ['l', 'm'], 'n': ['o']}}, \
      ]

  yields

      [{'name': 'a', 'children': ['b', 'c']},
      {'name': 'd', 'children': ['e']},
      ],
      [{'name': 'i', 'children': ['j']},
      {'name': 'f', 'children': ['g', 'h']},
      ],
      [{'name': 'k', 'spouses': ['l', 'm']},
      {'name': 'n', 'spouses': ['o']},
      ]
  """
  fathers_dict = biglist[0]['father']
  mothers_dict = biglist[1]['mother']
  spouses_dict = biglist[2]['spouse']

  # Make lists so that index in the lists gives a unique
  # identifier
  # Also makes room for later information
  fathers = []
  mothers = []
  spouses = []
  for father in fathers_dict:
    fathers.append(
      {'name': father, 'children': fathers_dict[father]}
    )
  for mother in mothers_dict:
    mothers.append(
      {'name': mother, 'children': mothers_dict[mother]}
    )
  for prime_spouse in spouses_dict:
    spouses.append(
      {'name': prime_spouse, 'spouses': spouses_dict[prime_spouse]}
    )

  return fathers, mothers, spouses


def yaml_to_family(yaml_file):
  family = Family()

  people, fathers, mothers, spouses = yaml.load_all(yaml_file)
  people  = people['people']
  fathers = fathers['father']
  mothers = mothers['mother']
  spouses = spouses['spouse']

  persons_dict = {}
  for person in people:
    for name, gender in person.iteritems():
      cur_person = Person(name=name, gender=gender)
      persons_dict[name] = cur_person
      family.add_person(cur_person)

  for father in fathers:
    father_person = persons_dict[father]
    children = [
        persons_dict[child_name]
        for child_name in fathers[father]
    ]
    family.add_children(father_person, children)

  for mother in mothers:
    mother_person = persons_dict[mother]
    children = [
        persons_dict[child_name]
        for child_name in mothers[mother]
    ]
    family.add_children(mother_person, children)

  for spouse in spouses:
    spouse_person = persons_dict[spouse]
    spouse_primes = [
        persons_dict[spouse_name]
        for spouse_name in spouses[spouse]
    ]
    family.add_spouses(spouse_person, spouse_primes)

  return family


def biglist_to_family(biglist):
  """
  Take `biglist` as would be returned from a .yaml file
  and return corresponding Family instance
  """
  return Family(*split_biglist(biglist))


def d3_html_page_generator(family):
  """Yield lines of an html page showing connections"""
  yield """<!DOCTYPE html>
  <meta charset="utf-8">
  <style>
  .link {
    fill: none;
    stroke: #666;
    stroke-width: 1.5px;
  }

  #mother {
    fill: red;
  }
  .link.mother {
    stroke: red;
  }

  #father {
    fill: blue;
  }
  .link.father {
    stroke: blue;
  }

  .link.spouse {
    stroke-dasharray: 0,7 1;
  }

  circle {
    fill: #ccc;
    stroke: #333;
    stroke-width: 1.5px;
  }

  text {
    font: 10px sans-serif;
    pointer-events: none;
    text-shadow: 0 1px 0 #fff, 1px 0 0 #fff, 0 -1px 0 #fff, -1px 0 0 #fff;
    background:red;
  }

  </style>
  <body>
  <script src="http://d3js.org/d3.v3.min.js"></script>
  <script>

  var links = [];

  function addRelation(sourcey, targety, relationy, listy) {
    listy.push({source: sourcey, target: targety, type: relationy})
  }
  family = {"""
  yield '  "father": {'
  for father in family.fathers():
    yield '"{}": ['.format(father.name)
    for child in family.children(father):
      yield '"{}",\n'.format(child)
    yield '],\n'
  yield '},\n'
  yield '"mother": {\n'
  for mother in family.mothers():
    yield '"{}": [\n'.format(mother.name)
    for child in family.children(mother):
      yield '"{}",\n'.format(child)
    yield '],\n'
  yield '},\n'
  yield '"spouse": {\n'
  for prime_spouse in family.spouses():
    yield '"{}": [\n'.format(prime_spouse.name)
    for spouse in family.all_spouses(prime_spouse):
      yield '"{}",\n'.format(spouse)
    yield '],\n'
  yield '}\n'
  yield """
}

for (var relation in family) {
  for (var relator in family[relation]) {
    if (family[relation].hasOwnProperty(relator)) {
      numChildren = family[relation][relator].length;
      for (var i = 0; i < numChildren; i++) {
        addRelation(relator, family[relation][relator][i], relation, links);
      }
    }
  }
}

var nodes = {};

// Compute the distinct nodes from the links.
links.forEach(function(link) {
  link.source = nodes[link.source] || (nodes[link.source] = {name: link.source});
  link.target = nodes[link.target] || (nodes[link.target] = {name: link.target});
});

var width = 2 * 1260,
    height = 2 * 800;

var force = d3.layout.force()
    .nodes(d3.values(nodes))
    .links(links)
    .size([width, height])
    .chargeDistance(400)
    .linkDistance(60)
    .gravity(0.01)
    .charge(-300)
    .on("tick", tick)
    .start();

var svg = d3.select("body").append("svg")
    .attr("width", width)
    .attr("height", height);

// Per-type markers, as they don't inherit styles.
svg.append("defs").selectAll("marker")
    .data(["father", "mother", "spouse"])
  .enter().append("marker")
    .attr("id", function(d) { return d; })
    .attr("viewBox", "0 -5 10 10")
    .attr("refX", 15)
    .attr("refY", -1.5)
    .attr("markerWidth", 6)
    .attr("markerHeight", 6)
    .attr("orient", "auto")
  .append("path")
    .attr("d", "M0,-5L10,0L0,5");

var path = svg.append("g").selectAll("path")
    .data(force.links())
  .enter().append("path")
    .attr("class", function(d) { return "link " + d.type; })
    .attr("marker-end", function(d) { return "url(#" + d.type + ")"; });

var circle = svg.append("g").selectAll("circle")
    .data(force.nodes())
  .enter().append("circle")
    .attr("r", 6)
    .call(force.drag);

var text = svg.append("g").selectAll("text")
    .data(force.nodes())
  .enter().append("text")
    .attr("x", 8)
    .attr("y", ".31em")
    .text(function(d) { return d.name; });

// Use elliptical arc path segments to doubly-encode directionality.
function tick() {
  path.attr("d", linkArc);
  circle.attr("transform", transform);
  text.attr("transform", transform);
}

function linkArc(d) {
  var dx = d.target.x - d.source.x,
      dy = d.target.y - d.source.y,
      dr = Math.sqrt(dx * dx + dy * dy);
  return "M" + d.source.x + "," + d.source.y + "A" + dr + "," + dr + " 0 0,1 " + d.target.x + "," + d.target.y;
}

function transform(d) {
  return "translate(" + d.x + "," + d.y + ")";
}

</script>
</body>
</html>
"""


def dot_file_generator(family):
  """Generate a graphviz .dot file"""

  yield "digraph family_tree {"

  # Set up the nodes
  for person_name in family.names():
    yield '  {} [label="{}", shape="box"];'.format(
        name_to_uid(person_name), person_name)

  # Set up the connections
  for father in family.fathers():
    for child in family.children(father):
      yield '  {} -> {} [color=blue];'.format(
          name_to_uid(father.name), 
          name_to_uid(child.name))
  for mother in family.mothers():
    for child in family.children(mother):
      yield '  {} -> {} [color=orange];'.format(
          name_to_uid(mother.name),
          name_to_uid(child.name))
  for prime_spouse in family.spouses():
    for spouse in family.all_spouses(prime_spouse):
      yield '  {} -> {} [style="dotted"];'.format(
          name_to_uid(prime_spouse.name),
          name_to_uid(spouse.name))
  yield "}"
