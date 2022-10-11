#!/usr/bin/env python3
import vobject

out_file = "kontakte.vcf"

contacts = []

# copy content from excel sheet to a text file (every column will be seperated by a tab \t
for line in open("input.txt"):
    # skip header
    if "Vorname" in line:
        continue
    # we are done if there is an empty line
    if line.strip() == "":
        break
    vorname, nachname, nummer = line.split("\t")
    nachname = nachname.strip()
    nummer = nummer.strip()

    # handle special case
    if "ist vorhanden" in nummer.lower():
        continue

    v = vobject.vCard()
    v.add('n')
    v.n.value = vobject.vcard.Name(family=nachname, given=vorname)
    v.add('fn')
    v.fn.value = f"{vorname} {nachname}"
    v.add('tel')
    v.tel.value = nummer
    v.tel.value_param = 'TEXT'
    contacts.append((v.serialize()))
    print(f"Adding {vorname} {nachname}")


with open(out_file, "w") as f:
    for contact in contacts:
        f.write(contact)

