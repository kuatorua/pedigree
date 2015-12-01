- [Package][] properly
- Generate `.svg` file from `.dot` in some purely Python way so that
  linux command line isn't necessary.
- Simple menu-based console program for inputting names as they're
  told to you by relatives.
  - Genealogy is usual spoken as "X and Y had these 3 kids: ..." and
    "X had 3 brothers: ..." both of which are complicated to enter
    into the `.yaml` file directly.
- Structure .yaml file so there's room for extra information like
  images and stories
  - Use images in some of the visualizations
- Handle empty `father`, `mother`, and/or `spouse` tables.
- Friendly errors when CLI specified files don't exist
- Make colors specifiable
- Give option to favory patriliny over matriliny or vice-versa
  to make a planar graph.

[Package]: http://blog.ionelmc.ro/2015/02/24/the-problem-with-packaging-in-python/