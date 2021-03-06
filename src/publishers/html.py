#!/usr/bin/python

import animal
import configuration
import db
import dbfs
import i18n
import lookups
import math
import onlineform
import os
import smcom
import sys
import users
import utils
import wordprocessor

from base import FTPPublisher
from sitedefs import BASE_URL, MULTIPLE_DATABASES_PUBLISH_FTP, MULTIPLE_DATABASES_PUBLISH_URL, SERVICE_URL

class HTMLPublisher(FTPPublisher):
    """
    Handles publishing to the internet via static HTML files to 
    an FTP server.
    """
    navbar = ""
    totalAnimals = 0
    user = "cron"

    def __init__(self, dbo, publishCriteria, user):
        l = dbo.locale
        # If we have a database override and it's not been ignored, use it
        if MULTIPLE_DATABASES_PUBLISH_FTP is not None and not configuration.publisher_ignore_ftp_override(dbo):
            c = MULTIPLE_DATABASES_PUBLISH_FTP
            publishCriteria.uploadDirectly = True
            publishCriteria.clearExisting = True
            publishCriteria.forceReupload = False
            publishCriteria.scaleImages = 1
            FTPPublisher.__init__(self, dbo, publishCriteria,
                self.replaceMDBTokens(dbo, c["host"]),
                self.replaceMDBTokens(dbo, c["user"]),
                self.replaceMDBTokens(dbo, c["pass"]),
                c["port"], 
                self.replaceMDBTokens(dbo, c["chdir"]),
                c["passive"])
        else:                
            FTPPublisher.__init__(self, dbo, publishCriteria, 
                configuration.ftp_host(dbo), configuration.ftp_user(dbo), configuration.ftp_password(dbo),
                configuration.ftp_port(dbo), configuration.ftp_root(dbo), configuration.ftp_passive(dbo))
        self.user = user
        self.initLog("html", i18n._("HTML/FTP Publisher", l))

    def escapePageName(self, s):
        suppress = [ " ", "(", ")", "/", "\\", "!", "?", "*" ]
        for x in suppress:
            s = s.replace(x, "_")
        return s

    def getPathFromStyle(self):
        """
        Looks at the publishing criteria and returns a DBFS path to get
        the template files from
        """
        if self.pc.style == ".": return "/internet"
        return "/internet/" + self.pc.style

    def getHeader(self):
        path = self.getPathFromStyle()
        self.log("Getting header style from: %s" % path)
        header = dbfs.get_string(self.dbo, "head.html", path)
        if header == "": header = dbfs.get_string(self.dbo, "pih.dat", path)
        if header == "":
            header = """<html>
            <head>
            <title>Animals Available For Adoption</title>
            </head>
            <body>
            <p>$$NAV$$</p>
            <table width="100%%">
            """
        return header

    def getFooter(self):
        path = self.getPathFromStyle()
        self.log("Getting footer style from: %s" % path)
        footer = dbfs.get_string(self.dbo, "foot.html", path)
        if footer == "": footer = dbfs.get_string(self.dbo, "pif.dat", path)
        if footer == "":
            footer = "</table></body></html>"
        return footer

    def getBody(self):
        path = self.getPathFromStyle()
        body = dbfs.get_string(self.dbo, "body.html", path)
        if body == "": body = dbfs.get_string(self.dbo, "pib.dat", path)
        if body == "":
            body = "<tr><td><img height=200 width=320 src=$$IMAGE$$></td>" \
                "<td><b>$$ShelterCode$$ - $$AnimalName$$</b><br>" \
                "$$BreedName$$ $$SpeciesName$$ aged $$Age$$<br><br>" \
                "<b>Details</b><br><br>$$WebMediaNotes$$<hr></td></tr>"
        return body

    def saveTemplateImages(self):
        """
        Saves all image files in the template folder to the publish directory
        """
        dbfs.get_files(self.dbo, "%.jp%g", self.getPathFromStyle(), self.publishDir)
        dbfs.get_files(self.dbo, "%.png", self.getPathFromStyle(), self.publishDir)
        dbfs.get_files(self.dbo, "%.gif", self.getPathFromStyle(), self.publishDir)
        # TODO: Upload these via FTP

    def substituteHFTag(self, searchin, page, user, title = ""):
        """
        Substitutes special header and footer tokens in searchin. page
        contains the current page number.
        """
        output = searchin
        nav = self.navbar.replace("<a href=\"%d.%s\">%d</a>" % (page, self.pc.extension, page), str(page))
        dateportion = i18n.python2display(self.locale, i18n.now(self.dbo.timezone))
        timeportion = i18n.format_date("%H:%M:%S", i18n.now(self.dbo.timezone))
        if page != -1:
            output = output.replace("$$NAV$$", nav)
        else:
            output = output.replace("$$NAV$$", "")
        output = output.replace("$$TITLE$$", title)
        output = output.replace("$$TOTAL$$", str(self.totalAnimals))
        output = output.replace("$$DATE$$", dateportion)
        output = output.replace("$$TIME$$", timeportion)
        output = output.replace("$$DATETIME$$", "%s %s" % (dateportion, timeportion))
        output = output.replace("$$VERSION$$", i18n.get_version())
        output = output.replace("$$REGISTEREDTO$$", configuration.organisation(self.dbo))
        output = output.replace("$$USER$$", "%s (%s)" % (user, users.get_real_name(self.dbo, user)))
        output = output.replace("$$ORGNAME$$", configuration.organisation(self.dbo))
        output = output.replace("$$ORGADDRESS$$", configuration.organisation_address(self.dbo))
        output = output.replace("$$ORGTEL$$", configuration.organisation_telephone(self.dbo))
        output = output.replace("$$ORGEMAIL$$", configuration.email(self.dbo))
        return output

    def substituteBodyTags(self, searchin, a):
        """
        Substitutes any tags in the body for animal data
        """
        tags = wordprocessor.animal_tags(self.dbo, a)
        tags["TotalAnimals"] = str(self.totalAnimals)
        tags["IMAGE"] = str(a["WEBSITEMEDIANAME"])
        # Note: WEBSITEMEDIANOTES becomes ANIMALCOMMENTS in get_animal_data when publisher_use_comments is on
        notes = utils.nulltostr(a["WEBSITEMEDIANOTES"])
        # Add any extra text
        notes += configuration.third_party_publisher_sig(self.dbo)
        # Preserve line endings in the bio
        notes = notes.replace("\n", "**le**")
        tags["WEBMEDIANOTES"] = notes 
        output = wordprocessor.substitute_tags(searchin, tags, True, "$$", "$$")
        output = output.replace("**le**", "<br />")
        return output

    def writeJavaScript(self, animals):
        # Remove original owner and other sensitive info from javascript database
        # before saving it
        for a in animals:
            for k in a.iterkeys():
                if k.startswith("ORIGINALOWNER") or k.startswith("BROUGHTINBY") \
                    or k.startswith("RESERVEDOWNER") or k.startswith("CURRENTOWNER") \
                    or k == "DISPLAYLOCATION":
                    a[k] = ""
        self.saveFile(os.path.join(self.publishDir, "db.js"), "publishDate='%s';animals=%s;" % (
            i18n.python2display(self.locale, i18n.now(self.dbo.timezone)), utils.json(animals)))
        if self.pc.uploadDirectly:
            self.log("Uploading javascript database...")
            self.upload("db.js")
            self.log("Uploaded javascript database.")

    def run(self):
        self.setLastError("")
        if self.isPublisherExecuting(): return
        self.updatePublisherProgress(0)
        self.setStartPublishing()
        self.executePages()
        if self.pc.htmlByChildAdult or self.pc.htmlBySpecies:
            self.executeAgeSpecies(self.user, self.pc.htmlByChildAdult, self.pc.htmlBySpecies)
        if self.pc.htmlByType:
            self.executeType(self.user)
        if self.pc.outputAdopted:
            self.executeAdoptedPage()
        if self.pc.outputDeceased:
            self.executeDeceasedPage()
        if self.pc.outputForms:
            self.executeFormsPage()
        if self.pc.outputRSS:
            self.executeRSS()
        self.cleanup()
        self.resetPublisherProgress()

    def executeAdoptedPage(self):
        """
        Generates and uploads the page of recently adopted animals
        """
        self.log("Generating adopted animals page...")

        user = self.user
        thisPage = ""
        thisPageName = "adopted.%s" % self.pc.extension
        totalAnimals = 0
        l = self.dbo.locale

        try:
            cutoff = i18n.subtract_days(i18n.now(self.dbo.timezone), self.pc.outputAdoptedDays)
            orderby = "a.AnimalName"
            if self.pc.order == 0: orderby = "a.ActiveMovementDate"
            elif self.pc.order == 1: orderby = "a.ActiveMovementDate DESC"
            elif self.pc.order == 2: orderby = "a.AnimalName"
            animals = db.query(self.dbo, animal.get_animal_query(self.dbo) + " WHERE a.ActiveMovementType = 1 AND " \
                "a.ActiveMovementDate >= %s AND a.DeceasedDate Is Null AND a.NonShelterAnimal = 0 "
                "ORDER BY %s" % (db.dd(cutoff), orderby))
            totalAnimals = len(animals)
            header = self.substituteHFTag(self.getHeader(), -1, user, i18n._("Recently adopted", l))
            footer = self.substituteHFTag(self.getFooter(), -1, user, i18n._("Recently adopted", l))
            body = self.getBody()
            thisPage = header
        except Exception as err:
            self.setLastError("Error setting up adopted page: %s" % err)
            self.logError("Error setting up adopted page: %s" % err, sys.exc_info())
            return

        anCount = 0
        for an in animals:
            try:
                anCount += 1
                self.log("Processing: %s: %s (%d of %d)" % ( an["SHELTERCODE"], an["ANIMALNAME"], anCount, totalAnimals))
                self.updatePublisherProgress(self.getProgress(anCount, len(animals)))

                # If the user cancelled, stop now
                if self.shouldStopPublishing(): 
                    self.log("User cancelled publish. Stopping.")
                    self.resetPublisherProgress()
                    self.cleanup()
                    return

                # upload images for this animal to our current FTP
                self.uploadImages(an, True)

                # Add to the page
                thisPage += self.substituteBodyTags(body, an)
                self.log("Finished processing: %s" % an["SHELTERCODE"])

            except Exception as err:
                self.logError("Failed processing animal: %s, %s" % (str(an["SHELTERCODE"]), err), sys.exc_info())

        # Append the footer, flush and upload the page
        thisPage += footer
        self.log("Saving page to disk: %s (%d bytes)" % (thisPageName, len(thisPage)))
        self.saveFile(os.path.join(self.publishDir, thisPageName), thisPage)
        self.log("Saved page to disk: %s" % thisPageName)
        if self.pc.uploadDirectly:
            self.log("Uploading page: %s" % thisPageName)
            self.upload(thisPageName)
            self.log("Uploaded page: %s" % thisPageName)

    def executeDeceasedPage(self):
        """
        Generates and uploads the page of recently deceased animals
        """
        self.log("Generating deceased animals page...")

        user = self.user
        thisPage = ""
        thisPageName = "deceased.%s" % self.pc.extension
        totalAnimals = 0
        l = self.dbo.locale

        try:
            cutoff = i18n.subtract_days(i18n.now(self.dbo.timezone), self.pc.outputAdoptedDays)
            orderby = "a.AnimalName"
            if self.pc.order == 0: orderby = "a.DeceasedDate"
            elif self.pc.order == 1: orderby = "a.DeceasedDate DESC"
            elif self.pc.order == 2: orderby = "a.AnimalName"
            animals = db.query(self.dbo, animal.get_animal_query(self.dbo) + " WHERE a.DeceasedDate Is Not Null AND " \
                "a.DeceasedDate >= %s AND a.NonShelterAnimal = 0 AND a.DiedOffShelter = 0 " \
                "ORDER BY %s" % (db.dd(cutoff), orderby))
            totalAnimals = len(animals)
            header = self.substituteHFTag(self.getHeader(), -1, user, i18n._("Recently deceased", l))
            footer = self.substituteHFTag(self.getFooter(), -1, user, i18n._("Recently deceased", l))
            body = self.getBody()
            thisPage = header
        except Exception as err:
            self.setLastError("Error setting up deceased page: %s" % err)
            self.logError("Error setting up deceased page: %s" % err, sys.exc_info())
            return

        anCount = 0
        for an in animals:
            try:
                anCount += 1
                self.log("Processing: %s: %s (%d of %d)" % ( an["SHELTERCODE"], an["ANIMALNAME"], anCount, totalAnimals))
                self.updatePublisherProgress(self.getProgress(anCount, len(animals)))

                # If the user cancelled, stop now
                if self.shouldStopPublishing(): 
                    self.log("User cancelled publish. Stopping.")
                    self.resetPublisherProgress()
                    self.cleanup()
                    return

                # upload images for this animal to our current FTP
                self.uploadImages(an, True)

                # Add to the page
                thisPage += self.substituteBodyTags(body, an)
                self.log("Finished processing: %s" % an["SHELTERCODE"])

            except Exception as err:
                self.logError("Failed processing animal: %s, %s" % (str(an["SHELTERCODE"]), err), sys.exc_info())

        # Append the footer, flush and upload the page
        thisPage += footer
        self.log("Saving page to disk: %s (%d bytes)" % (thisPageName, len(thisPage)))
        self.saveFile(os.path.join(self.publishDir, thisPageName), thisPage)
        self.log("Saved page to disk: %s" % thisPageName)
        if self.pc.uploadDirectly:
            self.log("Uploading page: %s" % thisPageName)
            self.upload(thisPageName)
            self.log("Uploaded page: %s" % thisPageName)

    def executeFormsPage(self):
        """
        Generates and uploads the page of online forms
        """
        self.log("Generating online forms page...")

        thisPageName = "forms.%s" % self.pc.extension
        thisPage = ""

        try:
            forms = onlineform.get_onlineforms(self.dbo)
            thisPage = "<html><head><title>Online Forms</title></head><body>"
            thisPage += "<h2>Online Forms</h2>"
            account = ""
            if smcom.active():
                account = "account=%s&" % self.dbo.database 
            for f in forms:
                thisPage += "<p><a target='_blank' href='%s?%smethod=online_form_html&formid=%d'>%s</a></p>" % (SERVICE_URL, account, f["ID"], f["NAME"])
            thisPage += "</body></html>"
        except Exception as err:
            self.setLastError("Error creating forms page: %s" % err)
            self.logError("Error creating forms page: %s" % err, sys.exc_info())
            return

        # Flush and upload the page
        self.log("Saving page to disk: %s (%d bytes)" % (thisPageName, len(thisPage)))
        self.saveFile(os.path.join(self.publishDir, thisPageName), thisPage)
        self.log("Saved page to disk: %s" % thisPageName)
        if self.pc.uploadDirectly:
            self.log("Uploading page: %s" % thisPageName)
            self.upload(thisPageName)
            self.log("Uploaded page: %s" % thisPageName)

    def executeAgeSpecies(self, user, childadult = True, species = True):
        """
        Publisher that puts animals on pages by age and species
        childadult: True if we should split up pages by animals under/over 6 months 
        species: True if we should split up pages by species
        """
        self.log("HTMLPublisher (age/species pages) starting...")

        l = self.dbo.locale
        normHeader = self.getHeader()
        normFooter = self.getFooter()
        body = self.getBody()
        header = self.substituteHFTag(normHeader, 0, user, i18n._("Available for adoption", l))
        footer = self.substituteHFTag(normFooter, 0, user, i18n._("Available for adoption", l))

        # Calculate the number of days old an animal has to be to
        # count as an adult
        childAdultSplitDays = self.pc.childAdultSplit * 7

        # Open FTP socket, bail if it fails
        if not self.openFTPSocket():
            self.setLastError("Failed opening FTP socket.")
            return

        try:
            animals = self.getMatchingAnimals()
            self.totalAnimals = len(animals)

            anCount = 0
            pages = {}

            # Create default pages for every possible permutation
            defaultpages = []
            if childadult and species:
                spec = lookups.get_species(self.dbo)
                for sp in spec:
                    defaultpages.append("adult%s" % sp["SPECIESNAME"])
                    defaultpages.append("baby%s" % sp["SPECIESNAME"])
            elif childadult:
                defaultpages = [ "adult", "baby" ]
            elif species:
                spec = lookups.get_species(self.dbo)
                for sp in spec:
                    defaultpages.append(sp["SPECIESNAME"])
            for dp in defaultpages:
                pages["%s.%s" % (dp, self.pc.extension)] = header

            # Create an all page
            allpage = "all.%s" % self.pc.extension
            pages[allpage] = header

        except Exception as err:
            self.logError("Error setting up page: %s" % err, sys.exc_info())
            self.setLastError("Error setting up page: %s" % err)
            return

        for an in animals:
            try:
                anCount += 1

                # If a limit was set, stop now
                if self.pc.limit > 0 and anCount > self.pc.limit:
                    self.log("Hit publishing limit of %d animals. Stopping." % self.pc.limit)
                    break

                self.log("Processing: %s: %s (%d of %d)" % ( an["SHELTERCODE"], an["ANIMALNAME"], anCount, self.totalAnimals))
                self.updatePublisherProgress(self.getProgress(anCount, len(animals)))

                # If the user cancelled, stop now
                if self.shouldStopPublishing(): 
                    self.log("User cancelled publish. Stopping.")
                    self.resetPublisherProgress()
                    self.cleanup()
                    return

                # upload all images for this animal to our current FTP
                self.uploadImages(an, True)
                
                # Calculate the new page name
                pagename = ".%s" % self.pc.extension
                if species:
                    pagename = "%s%s" % (an["SPECIESNAME"], pagename)
                if childadult:
                    days = i18n.date_diff_days(an["DATEOFBIRTH"], i18n.now(self.dbo.timezone))
                    if days < childAdultSplitDays:
                        pagename = "baby%s" % pagename
                    else:
                        pagename = "adult%s" % pagename

                # Does this page exist?
                if pagename not in pages:
                    # No, create it and add the header
                    page = header
                else:
                    page = pages[pagename]

                # Add this item to the page
                page += self.substituteBodyTags(body, an)
                pages[pagename] = page
                self.log("%s -> %s" % (an["SHELTERCODE"], pagename))

                # Add this item to our magic "all" page
                page = pages[allpage]
                page += self.substituteBodyTags(body, an)
                pages[allpage] = page
                
                # Mark success in the log
                self.log("Processed: %s: %s (%d of %d)" % ( an["SHELTERCODE"], an["ANIMALNAME"], anCount, len(animals)))

            except Exception as err:
                self.logError("Failed processing animal: %s, %s" % (str(an["SHELTERCODE"]), err), sys.exc_info())

        # Mark published
        self.markAnimalsPublished(animals)

        # Upload the pages
        for k, v in pages.iteritems():
            self.log("Saving page to disk: %s (%d bytes)" % (k, len(v + footer)))
            self.saveFile(os.path.join(self.publishDir, self.escapePageName(k)), v + footer)
            self.log("Saved page to disk: %s" % k)
            if self.pc.uploadDirectly:
                self.log("Uploading page: %s" % k)
                self.upload(self.escapePageName(k))
                self.log("Uploaded page: %s" % k)

    def executePages(self):
        """
        Publisher based on assigning animals to pages.
        """

        self.log("HTMLPublisher (numbered pages) starting...")

        user = self.user
        normHeader = self.getHeader()
        normFooter = self.getFooter()
        body = self.getBody()
        l = self.dbo.locale

        # Open FTP socket, bail if it fails
        if not self.openFTPSocket():
            self.setLastError("Failed opening FTP socket.")
            return

        try:
            animals = self.getMatchingAnimals()
            self.totalAnimals = len(animals)
            noPages = 0
            animalsPerPage = self.pc.animalsPerPage
            pages = {}

            # Calculate pages required
            if self.totalAnimals <= animalsPerPage:
                noPages = 1
            else:
                noPages = math.ceil(float(self.totalAnimals) / float(animalsPerPage))

            # Page navigation bar
            if noPages > 1:
                self.navbar = ""
                for i in range(1, int(noPages + 1)):
                    self.navbar += "<a href=\"%d.%s\">%d</a>&nbsp;" % ( i, self.pc.extension, i )

            # Start a new page with a header
            thisPageName = "1.%s" % self.pc.extension
            currentPage = 1
            itemsOnPage = 0

            # Substitute tags in the header and footer
            header = self.substituteHFTag(normHeader, currentPage, user, i18n._("Available for adoption", l))
            footer = self.substituteHFTag(normFooter, currentPage, user, i18n._("Available for adoption", l))
            thisPage = header
            anCount = 0

            # Clear any existing uploaded images
            if self.pc.forceReupload:
                self.clearExistingImages()

        except Exception as err:
            self.setLastError("Error setting up page: %s" % err)
            self.logError("Error setting up page: %s" % err, sys.exc_info())
            return

        for an in animals:
            try:
                anCount += 1

                # If a limit was set, stop now
                if self.pc.limit > 0 and anCount > self.pc.limit:
                    self.log("Hit publishing limit of %d animals. Stopping." % self.pc.limit)
                    break

                self.log("Processing: %s: %s (%d of %d)" % ( an["SHELTERCODE"], an["ANIMALNAME"], anCount, self.totalAnimals))
                self.updatePublisherProgress(self.getProgress(anCount, len(animals)))

                # If the user cancelled, stop now
                if self.shouldStopPublishing(): 
                    self.log("User cancelled publish. Stopping.")
                    self.resetPublisherProgress()
                    self.cleanup()
                    return

                # upload all images for this animal to our current FTP
                self.uploadImages(an, True)
                
                # Slot free on this page?
                if itemsOnPage < animalsPerPage:
                    thisPage += self.substituteBodyTags(body, an)
                    itemsOnPage += 1
                    self.log("%s -> %s" % (an["SHELTERCODE"], thisPageName))
                else:
                    self.log("Current page complete.")
                    # No, append the footer, store the page
                    thisPage += footer
                    pages[thisPageName] = thisPage
                    # New page
                    currentPage += 1
                    thisPageName = "%d.%s" % ( currentPage, self.pc.extension )
                    header = self.substituteHFTag(normHeader, currentPage, user, i18n._("Available for adoption", l))
                    footer = self.substituteHFTag(normFooter, currentPage, user, i18n._("Available for adoption", l))
                    thisPage = header
                    # Append this animal
                    thisPage += self.substituteBodyTags(body, an)
                    itemsOnPage = 1
                    self.log("%s -> %s" % (an["SHELTERCODE"], thisPageName))
                
                # Mark success in the log
                self.logSuccess("Processed: %s: %s (%d of %d)" % ( an["SHELTERCODE"], an["ANIMALNAME"], anCount, len(animals)))

            except Exception as err:
                self.logError("Failed processing animal: %s, %s" % (str(an["SHELTERCODE"]), err), sys.exc_info())

        # Mark published
        self.markAnimalsPublished(animals, first=True)

        # Done with animals, store the final page
        thisPage += footer
        pages[thisPageName] = thisPage

        # Clear any existing uploaded pages
        if self.pc.clearExisting: 
            self.clearExistingHTML()

        # Upload the new pages
        for k, v in pages.iteritems():
            self.log("Saving page to disk: %s (%d bytes)" % (k, len(v)))
            self.saveFile(os.path.join(self.publishDir, k), v)
            self.log("Saved page to disk: %s" % k)
            if self.pc.uploadDirectly:
                self.log("Uploading page: %s" % k)
                self.upload(k)
                self.log("Uploaded page: %s" % k)

        # Handle javascript db
        if self.pc.generateJavascriptDB:
            self.writeJavaScript(animals)

        # Save any additional images required by the template
        self.saveTemplateImages()

    def executeRSS(self):
        """
        Generates and uploads the rss.xml page
        """
        def rss_header():
            return """<?xml version="1.0" encoding="UTF-8"?>
                <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/" >
                <channel rdf:about="http://www.mydomain.com">
                <title>Animals for Adoption at $$ORGNAME$$</title>
                <description></description>
                <link>RDFLINK</link>
                </channel>"""
        def rss_body():
            return """<item rdf:about="RDFLINK">
                <title>$$ShelterCode$$ - $$AnimalName$$ ($$BreedName$$ $$SpeciesName$$ aged $$Age$$)</title>
                <link>RDFLINK</link>
                <description>
                &lt;img src="$$WebMediaFilename$$" align="left" /&gt;
                $$WebMediaNotes$$
                </description>
                </item>"""
        def rss_footer():
            return """</rdf:RDF>"""

        self.log("Generating rss.xml page...")

        user = self.user
        thisPage = ""
        thisPageName = "rss.xml"
        totalAnimals = 0
        link = MULTIPLE_DATABASES_PUBLISH_URL
        link = self.replaceMDBTokens(self.dbo, link)
        if link == "": link = BASE_URL

        try:
            animals = self.getMatchingAnimals()
            totalAnimals = len(animals)
            header = dbfs.get_string(self.dbo, "head.html", "/internet/rss")
            footer = dbfs.get_string(self.dbo, "foot.html", "/internet/rss")
            body = dbfs.get_string(self.dbo, "body.html", "/internet/rss")
            if header == "": header = rss_header()
            if footer == "": footer = rss_footer()
            if body == "": body = rss_body()
            header = self.substituteHFTag(header, 1, user)
            footer = self.substituteHFTag(footer, 1, user)
            thisPage = header
        except Exception as err:
            self.setLastError("Error setting up rss.xml: %s" % err)
            self.logError("Error setting up rss.xml: %s" % err, sys.exc_info())
            return

        anCount = 0
        for an in animals:
            try:
                anCount += 1
                self.log("Processing: %s: %s (%d of %d)" % ( an["SHELTERCODE"], an["ANIMALNAME"], anCount, totalAnimals))
                self.updatePublisherProgress(self.getProgress(anCount, len(animals)))

                # If the user cancelled, stop now
                if self.shouldStopPublishing(): 
                    self.log("User cancelled publish. Stopping.")
                    self.resetPublisherProgress()
                    self.cleanup()
                    return

                # Images already uploaded by Page/Species publisher

                # Add to the page
                thisPage += self.substituteBodyTags(body, an)
                self.log("Finished processing: %s" % an["SHELTERCODE"])

            except Exception as err:
                self.logError("Failed processing animal: %s, %s" % (str(an["SHELTERCODE"]), err), sys.exc_info())

        # Append the footer, flush and upload the page
        thisPage += footer
        thisPage = thisPage.replace("RDFLINK", link)
        self.log("Saving page to disk: %s (%d bytes)" % (thisPageName, len(thisPage)))
        self.saveFile(os.path.join(self.publishDir, thisPageName), thisPage)
        self.log("Saved page to disk: %s" % thisPageName)
        if self.pc.uploadDirectly:
            self.log("Uploading page: %s" % thisPageName)
            self.upload(thisPageName)
            self.log("Uploaded page: %s" % thisPageName)

    def executeType(self, user):
        """
        Publisher that puts animals on pages by type
        """
        self.log("HTMLPublisher (type) starting...")

        l = self.dbo.locale
        normHeader = self.getHeader()
        normFooter = self.getFooter()
        body = self.getBody()
        header = self.substituteHFTag(normHeader, 0, user, i18n._("Available for adoption", l))
        footer = self.substituteHFTag(normFooter, 0, user, i18n._("Available for adoption", l))

        # Open FTP socket, bail if it fails
        if not self.openFTPSocket():
            self.setLastError("Failed opening FTP socket.")
            return

        try:
            animals = self.getMatchingAnimals()
            self.totalAnimals = len(animals)

            anCount = 0
            pages = {}

            # Create default pages for every possible permutation
            defaultpages = []
            atype = lookups.get_animal_types(self.dbo)
            for atype in lookups.get_animal_types(self.dbo):
                defaultpages.append(atype["ANIMALTYPE"])
            for dp in defaultpages:
                pages["%s.%s" % (dp, self.pc.extension)] = header

            # Create an all page
            allpage = "all.%s" % self.pc.extension
            pages[allpage] = header

        except Exception as err:
            self.logError("Error setting up page: %s" % err, sys.exc_info())
            self.setLastError("Error setting up page: %s" % err)
            return

        for an in animals:
            try:
                anCount += 1

                # If a limit was set, stop now
                if self.pc.limit > 0 and anCount > self.pc.limit:
                    self.log("Hit publishing limit of %d animals. Stopping." % self.pc.limit)
                    break

                self.log("Processing: %s: %s (%d of %d)" % ( an["SHELTERCODE"], an["ANIMALNAME"], anCount, self.totalAnimals))
                self.updatePublisherProgress(self.getProgress(anCount, len(animals)))

                # If the user cancelled, stop now
                if self.shouldStopPublishing(): 
                    self.log("User cancelled publish. Stopping.")
                    self.resetPublisherProgress()
                    self.cleanup()
                    return

                # upload all images for this animal to our current FTP
                self.uploadImages(an, True)
                
                # Calculate the new page name
                pagename = "%s.%s" % (an["ANIMALTYPENAME"], self.pc.extension)

                # Does this page exist?
                if pagename not in pages:
                    # No, create it and add the header
                    page = header
                else:
                    page = pages[pagename]

                # Add this item to the page
                page += self.substituteBodyTags(body, an)
                pages[pagename] = page
                self.log("%s -> %s" % (an["SHELTERCODE"], pagename))

                # Add this item to our magic "all" page
                page = pages[allpage]
                page += self.substituteBodyTags(body, an)
                pages[allpage] = page
                
                # Mark success in the log
                self.log("Processed: %s: %s (%d of %d)" % ( an["SHELTERCODE"], an["ANIMALNAME"], anCount, len(animals)))

            except Exception as err:
                self.logError("Failed processing animal: %s, %s" % (str(an["SHELTERCODE"]), err), sys.exc_info())

        # Mark published
        self.markAnimalsPublished(animals)

        # Upload the pages
        for k, v in pages.iteritems():
            self.log("Saving page to disk: %s (%d bytes)" % (k, len(v + footer)))
            self.saveFile(os.path.join(self.publishDir, self.escapePageName(k)), v + footer)
            self.log("Saved page to disk: %s" % k)
            if self.pc.uploadDirectly:
                self.log("Uploading page: %s" % k)
                self.upload(self.escapePageName(k))
                self.log("Uploaded page: %s" % k)


