#!/usr/bin/python

import configuration
import i18n
import sys
import utils

from base import AbstractPublisher, get_microchip_data
from sitedefs import PETLINK_BASE_URL

class PetLinkPublisher(AbstractPublisher):
    """
    Handles publishing of updated microchip info to PetLink.net
    """
    def __init__(self, dbo, publishCriteria):
        publishCriteria.uploadDirectly = True
        publishCriteria.thumbnails = False
        AbstractPublisher.__init__(self, dbo, publishCriteria)
        self.initLog("petlink", "PetLink Publisher")

    def plYesNo(self, condition):
        """
        Returns yes or no for a condition.
        """
        if condition:
            return "y"
        else:
            return "n"

    def plBreed(self, breedname, speciesname, iscross):
        """
        Returns a PetLink breed of either the breed name,
        "Mixed Breed" if iscross == 1 or "Other" if the species
        is not Cat or Dog.
        """
        if speciesname.lower().find("cat") != -1 and speciesname.lower().find("dog") != -1:
            return "Other"
        if iscross == 1:
            return "Mixed Breed"
        return breedname

    def run(self):
        
        self.log("PetLinkPublisher starting...")

        if self.isPublisherExecuting(): return
        self.updatePublisherProgress(0)
        self.setLastError("")
        self.setStartPublishing()

        email = configuration.petlink_email(self.dbo)
        password = configuration.petlink_password(self.dbo)
        chippass = configuration.petlink_chippassword(self.dbo)
        baseurl = PETLINK_BASE_URL

        if email == "" or password == "":
            self.setLastError("No PetLink login has been set.")
            return

        if chippass == "" or baseurl == "":
            self.setLastError("baseurl and chippass need to be set for petlink.com publisher")
            return

        animals = get_microchip_data(self.dbo, ['98102',], "petlink")
        if len(animals) == 0:
            self.setLastError("No animals found to publish.")
            return

        LOGIN_URL = baseurl + "j_acegi_security_check"
        UPLOAD_URL = baseurl + "animalprofessional/massImportUpload.spring"
        WELCOME_URL = baseurl + "cms2.spring?path=/welcome.html"

        # Login via HTTP
        fields = {
            "j_username": email,
            "j_password": password
        }
        try:
            self.log("Getting PetLink welcome page...")
            r = utils.get_url(WELCOME_URL)
            try:
                rcookies = r["cookies"]
                sessionid = rcookies["JSESSIONID"]
            except KeyError:
                self.setLastError("Login failed (no JSESSIONID cookie).")
                self.saveLog()
                return
            self.log("Homepage returned headers: %s" % r["headers"])
            self.log("Found session cookie: %s" % sessionid)
            self.log("Logging in to PetLink.net... ")
            r = utils.post_form(LOGIN_URL, fields, cookies = rcookies)
            if r["response"].find("incorrect user name or password") != -1:
                self.setLastError("Login failed (invalid username or password)")
                self.saveLog()
                return
            elif r["response"].find("Hello") == -1:
                self.setLastError("Login failed (no Hello found).")
                self.log("response: headers=%s, body=%s" % (r["headers"], r["response"]))
                self.saveLog()
                return
            else:
                self.log("Login to PetLink successful.")
        except Exception as err:
            self.logError("Failed logging in: %s" % err, sys.exc_info())
            self.setLastError("Login failed (error during HTTP request).")
            self.saveLog()
            return

        anCount = 0
        csv = []
        processed_animals = []
        csv.append("Software,TransactionType,MicrochipID,FirstName,LastName,Address,City,State,ZipCode,Country," \
            "Phone1,Phone2,Phone3,Email,Password,Date_of_Implant,PetName,Species,Breed,Gender," \
            "Spayed_Neutered,ColorMarkings")
        for an in animals:
            try:
                line = []
                anCount += 1
                self.log("Processing: %s: %s (%d of %d) - %s" % ( an["SHELTERCODE"], an["ANIMALNAME"], anCount, len(animals), an["IDENTICHIPNUMBER"]))
                self.updatePublisherProgress(self.getProgress(anCount, len(animals)))

                # If the user cancelled, stop now
                if self.shouldStopPublishing(): 
                    self.log("User cancelled publish. Stopping.")
                    self.resetPublisherProgress()
                    return

                # If the microchip number isn't 15 digits, skip it
                if len(an["IDENTICHIPNUMBER"].strip()) != 15:
                    self.logError("Chip number failed validation (%s not 15 digits), skipping." % an["IDENTICHIPNUMBER"])
                    continue

                # Validate certain items aren't blank so we aren't registering bogus data
                if utils.nulltostr(an["CURRENTOWNERADDRESS"].strip()) == "":
                    self.logError("Address for the new owner is blank, cannot process")
                    continue 

                if utils.nulltostr(an["CURRENTOWNERPOSTCODE"].strip()) == "":
                    self.logError("Postal code for the new owner is blank, cannot process")
                    continue

                # If there's no email or home phone, PetLink won't accept it
                email = utils.nulltostr(an["CURRENTOWNEREMAILADDRESS"]).strip()
                homephone = utils.nulltostr(an["CURRENTOWNERHOMETELEPHONE"]).strip()
                workphone = utils.nulltostr(an["CURRENTOWNERWORKTELEPHONE"]).strip()
                mobilephone = utils.nulltostr(an["CURRENTOWNERMOBILETELEPHONE"]).strip()
                if email == "" and homephone == "" and workphone == "" and mobilephone == "":
                    self.logError("No email address or phone number for owner, skipping.")
                    continue
                
                # If we don't have an email address, use the owner's
                # best phone number (home, mobile then work) @petlink.tmp
                if email == "":
                    phone = homephone or mobilephone or workphone
                    email = "".join(c for c in phone if c.isdigit())
                    email = "%s@petlink.tmp" % email

                # Software
                line.append("\"ASM\"")
                # TransactionType
                line.append("\"%s\"" % ( self.getLastPublishedDate(an["ID"]) is None and 'N' or 'T' ))
                # MicrochipID
                line.append("\"%s\"" % ( an["IDENTICHIPNUMBER"] ))
                # FirstName
                line.append("\"%s\"" % ( an["CURRENTOWNERFORENAMES"] ))
                # LastName
                line.append("\"%s\"" % ( an["CURRENTOWNERSURNAME"] ))
                # Address
                line.append("\"%s\"" % ( an["CURRENTOWNERADDRESS"] ))
                # City
                line.append("\"%s\"" % ( an["CURRENTOWNERTOWN"] ))
                # State
                line.append("\"%s\"" % ( an["CURRENTOWNERCOUNTY"] ))
                # ZipCode
                line.append("\"%s\"" % ( an["CURRENTOWNERPOSTCODE"] ))
                # Country
                line.append("\"USA\"")
                # Phone1
                line.append("\"%s\"" % ( an["CURRENTOWNERHOMETELEPHONE"] ))
                # Phone2
                line.append("\"%s\"" % ( an["CURRENTOWNERWORKTELEPHONE"] ))
                # Phone3
                line.append("\"%s\"" % ( an["CURRENTOWNERMOBILETELEPHONE"] ))
                # Email (mandatory)
                line.append("\"%s\"" % ( email ))
                # Password (config item, unique to each shelter)
                line.append("\"%s\"" % chippass)
                # Date_of_Implant (yy-mm-dd)
                line.append("\"%s\"" % i18n.format_date("%y-%m-%d", an["IDENTICHIPDATE"]))
                # PetName
                line.append("\"%s\"" % an["ANIMALNAME"])
                # Species
                line.append("\"%s\"" % an["SPECIESNAME"])
                # Breed (or "Mixed Breed" for crossbreeds, Other for animals not cats and dogs)
                line.append("\"%s\"" % self.plBreed(an["BREEDNAME1"], an["SPECIESNAME"], an["CROSSBREED"]))
                # Gender
                line.append("\"%s\"" % an["SEXNAME"])
                # Spayed_Neutered (y or n)
                line.append("\"%s\"" % self.plYesNo(an["NEUTERED"]))
                # ColorMarkings (our BaseColour field)
                line.append("\"%s\"" % an["BASECOLOURNAME"])
                # Add to our data file.  
                csv.append(",".join(line))
                # Remember we included this one
                processed_animals.append(an)
                # Mark success in the log
                self.logSuccess("Processed: %s: %s (%d of %d)" % ( an["SHELTERCODE"], an["ANIMALNAME"], anCount, len(animals)))
            except Exception as err:
                self.logError("Failed processing animal: %s, %s" % (str(an["SHELTERCODE"]), err), sys.exc_info())

        # If we excluded our only animals and have nothing to send, stop now
        if len(csv) == 1:
            self.log("No animals left to send to PetLink.")
            self.saveLog()
            self.setPublisherComplete()
            return

        # POST the csv file
        files = {
            "file": ( "import.csv", "\n".join(csv), "text/csv")
        }
        self.log("Uploading data file (%d csv lines) to %s..." % (len(csv), UPLOAD_URL))
        try:
            r = utils.post_multipart(url=UPLOAD_URL, files=files, cookies=rcookies)
            self.log("(%s redirects) req hdr: %s, \nreq data: %s" % (r["redirects"], r["requestheaders"], r["requestbody"]))

            # Look for any errors in the response
            for e in utils.regex_multi("id=(\d+?), transponder: (.+?)</li>", r["response"]):
                chip = e[0]
                message = e[1]

                # Iterate over a copy of the processed list so we can remove this animal from it
                for an in processed_animals[:]:
                    if an["IDENTICHIPNUMBER"] == chip:
                        # Remove this animal from the processed list
                        processed_animals.remove(an)
                        self.logError("%s: %s (%s) - Received error message from PetLink: %s" % \
                            (an["SHELTERCODE"], an["ANIMALNAME"], an["IDENTICHIPNUMBER"], message))
                        # If the message was that the chip is already registered,
                        # mark the animal as published but at the intake date -
                        # this will force this publisher to put it through as a transfer
                        # next time
                        if message.startswith("This microchip code has already been registered"):
                            self.markAnimalPublished(an["ID"], an["DATEBROUGHTIN"])
                            self.log("%s: %s (%s) - Already registered, marking as PetLink TRANSFER for next publish" % \
                                (an["SHELTERCODE"], an["ANIMALNAME"], an["IDENTICHIPNUMBER"]))

            if r["response"].find("Upload Completed") != -1:
                # Mark published
                self.log("Got successful upload response, marking processed animals as sent to petlink")
                self.markAnimalsPublished(processed_animals)
            else:
                self.logError("didn't find successful response, abandoning.")
                self.log("response hdr: %s, \nresponse: %s" % (r["headers"], r["response"]))
        except Exception as err:
            self.logError("Failed uploading data file: %s" % err)

        self.saveLog()
        self.setPublisherComplete()


