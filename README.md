# Old Roadside Pictures

This script grabs images from the [John Margolies Roadside America Photograph archive](https://www.loc.gov/rr/print/coll/john-margolies-roadside-america-photograph-archive.html) in the Library of Congress, adds a caption from the metadata, and then posts the combination to accounts at [Twitter](https://twitter.com/oldroadside) and [Mastodon](https://botsin.space/@oldroadside).

The large CSV file contains information about all 11,707 items in the collection; `nogo.txt` contains the indexes of items that the bot should not tweet (in most cases, because the photographs depict racist or otherwise offensive displays).

On first run, the bot will produce an `order.txt` which contains a randomized list of indexes that the bot will subsequently follow. That list is just a flat text file and can be edited accordingly.
