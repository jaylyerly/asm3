#!/usr/bin/env python

import asm
import sys
import requests

"""
Import script for Shelter Exchange CSV export.
It can be accessed by going to Animals tab and then Export

5th August, 2017
"""

infile = sys.argv[1]
asm.stderr("Importing file: %s" % infile)

# --- START OF CONVERSION ---

owners = []
movements = []
animals = []

asm.setid("animal", 100)
asm.setid("owner", 100)
asm.setid("adoption", 100)
asm.setid("dbfs", 100)
asm.setid("media", 100)

print "\\set ON_ERROR_STOP\nBEGIN;"
print "DELETE FROM animal WHERE ID >= 100 AND CreatedBy LIKE '%conversion';"
print "DELETE FROM owner WHERE ID >= 100 AND CreatedBy = 'conversion';"
print "DELETE FROM adoption WHERE ID >= 100 AND CreatedBy = 'conversion';"
print "DELETE FROM dbfs WHERE ID >= 100;"
print "DELETE FROM media WHERE ID >= 100;"

data = asm.csv_to_list(infile)


def addOwner(name):
    o = asm.Owner()
    o.OwnerSurname = name
    o.OwnerName = name
    owners.append(o)
    return o

uo = addOwner("Unknown Owner")
spca = addOwner("SPCA")
wcac = addOwner("WCAC")
foster = addOwner("Unknown Foster")
foster.IsFosterer = 1

dl_count = 0

for d in data:
    a = asm.Animal()
    animals.append(a)
    a.SpeciesID = 7
    a.AnimalName = d["Name"]

    a.BreedID = asm.breed_id_for_name(d["Primary Breed"])
    a.Breed2ID = a.BreedID
    a.BreedName = asm.breed_name_for_id(a.BreedID)

    a.Sex = asm.getsex_mf(d["Sex"])
    a.Size = asm.size_from_db(d["Size"])

    a.Weight = asm.cfloat(d["Weight"])

    desc = d["Description"] 
    desc = desc.replace("No description provided", "")
    desc = desc.replace("<p>", "")
    desc = desc.replace("</p>", "")
    desc = desc.replace("<br />", "\n")
    a.AnimalComments = desc

    spNeedsDesc = d["Special Needs Description"].strip()
    if spNeedsDesc != "":
        a.HiddenAnimalDetails = spNeedsDesc

    a.BaseColourID = asm.colour_id_for_name(d["Color"], True)

    a.Neutered = asm.iif(d["Sterilized"] == 'Y', 1, 0)

    dob = d.get("Date of Birth")
    if dob == "":
        dob = "2000-01-01"
    a.DateOfBirth = asm.getdate_iso(dob)

    arrival = d.get("Arrival Date")
    if arrival == "":
        arrival = "2000-01-01"
    a.DateBroughtIn = asm.getdate_iso(arrival)

    a.HasSpecialNeeds = asm.iif(d["Has Special Needs"] == 'Y', 1, 0)

    status = d.get("Status").lower()

    def addMovementForOwner(o, movement_type, archive=False):
        """
        Movement types:
          0 | None
          1 | Adoption
          2 | Foster
          3 | Transfer
          4 | Escaped
          5 | Reclaimed
          6 | Stolen
          7 | Released To Wild
          8 | Retailer
          9 | Reservation
         10 | Cancelled Reservation
         11 | Trial Adoption
         12 | Permanent Foster
        """

        m = asm.Movement()
        movements.append(m)
        m.OwnerID = o.ID
        m.AnimalID = a.ID
        m.MovementDate = asm.getdate_iso("2017-01-01")
        m.MovementType = 1
        m.Comments = "Shelter Exchange import"
        a.ActiveMovementDate = m.MovementDate
        a.ActiveMovementType = movement_type 
        a.ActiveMovementID = m.ID
        if archive:
            a.Archived = 1

    if status == "transferred":
        addMovementForOwner(spca, movement_type=3)
        a.Archived = 1

    if status == "adopted":
        addMovementForOwner(uo, movement_type=1)
        a.Archived = 1

    if status == "reclaimed":
        addMovementForOwner(wcac, movement_type=1)
        a.Archived = 1

    # if status == "foster care":
        # addMovementForOwner(foster, movement_type=2)

    if status == "deceased":
        a.DeceasedDate = asm.getdate_iso("2017-01-01")
        a.Archived = 1

    def add_image_from_url(url):
        global dl_count
        if url == "":
            return
        asm.stderr("%s -- Downloading file: %s" % (dl_count, url))
        dl_count += 1
        response = requests.get(url, stream=True)
        imagedata = response.raw.data
        if imagedata is not None:
            asm.animal_image(a.ID, imagedata)

    add_image_from_url(d["Photo1"])
    add_image_from_url(d["Photo2"])
    add_image_from_url(d["Photo3"])
    add_image_from_url(d["Photo4"])


# Now that everything else is done, output stored records
for a in animals:
    print a
for o in owners:
    print o
for m in movements:
    print m

asm.stderr_summary(animals=animals, owners=owners, movements=movements)

print "DELETE FROM configuration WHERE ItemName LIKE 'DBView%';"
print "COMMIT;"

