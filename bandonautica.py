'''
------------------------------------------------------------------------------------------------------------------
   ______    _____    __     __) ______     ___   __     __) _____   __     __) ______) _____ )   ___    _____   
  (, /    ) (, /  |  (, /|  /   (, /    ) /(,  ) (, /|  /   (, /  | (, /   /   (, /    (, /  (__/_____) (, /  |  
    /---(     /---|    / | /      /    / /    /    / | /      /---|   /   /      /       /     /          /---|  
 ) / ____) ) /    |_) /  |/     _/___ /_/    /  ) /  |/    ) /    |_ /   /    ) /    ___/__   /        ) /    |_ 
(_/ (     (_/      (_/   '    (_/___ / (___ /  (_/   '    (_/       (___(_   (_/   (__ /     (______) (_/        
                                                                                                                 
-----------------------------------------------------------------------------------------------------------------
'''
import random
import re  # for making sense of the javascript on the bandcamp pages
import datetime  # for scrobbling (gets timestamp)
import time
import webbrowser # for opening artist page when presing the LINK button
from io import BytesIO # for saving and displaying covers
import os
#------------externals--------------------
import PySimpleGUI as sg #gui chotarda
import requests #for scrapping
from bs4 import BeautifulSoup #for scrapping
from pygame import mixer  # for playing mp3s, sigh...
import pylast  # for scrobbling
from PIL import Image  # for saving and displaying covers
from selenium import webdriver # for scrapping the tag pages
import mutagen.id3 #for tagging downloaded mp3
from mutagen.easyid3 import EasyID3
#-----------------------------------------

def print2log(text=""):
    global debuglog
    print(text)
    debuglog += text + "\n"    

def clean_string(text):
    text = re.sub(r'[\\~#%&*{}/:<>?|\"-]+', "'", text)
    text = text.replace("/", "")
    return text

def scrobble_track(artist, song):
    API_KEY = "75d60612ae46fa6aaf0bb3f3d3696ce0"
    API_SECRET = "6051e11d0441538951baed47117f553b"
    password = pylast.md5(LASTFM_PASSWORD)

    lastfm = pylast.LastFMNetwork(api_key=API_KEY, api_secret=API_SECRET,
                                  username=LASTFM_USERNAME, password_hash=password)

    unix_timestamp = int(time.mktime(datetime.datetime.now().timetuple()))
    lastfm.scrobble(artist=artist, title=song, timestamp=unix_timestamp)

def update_bar(progress):
    progress_bar.UpdateBar(progress)
    window.refresh()  # hack para esquivar el 'Not Responding' de la GUI

def generate_random_numbers(quantum=False):
    rep_num = 4 #the old 'numbers per set'
    max_num = 9999
    random_list = []
    if quantum:
        print2log("retrieving random quantum numbers...") 
        try:
            form_data = {
                "repeats":"norepeat",
                "set_num":"1",
                "rep_num":f"{rep_num}",
                "min_num":"1",
                "max_num":f"{max_num}",
                "action":"dice_action",
                "dice_nonce_field":"ca3333e237",
                "_wp_http_referer":"/live-numbers/dice-throw/"
            }
            url = "https://qrng.anu.edu.au/wp-admin/admin-ajax.php"
            response = requests.post(url, data=form_data)
            # response.text example "{\"type\":\"success\",\"output\":[[6837,463,2692,6724,3871,2540]]}"
            numbers = re.findall(r"\[\[(.*?)\]\]", response.text)[0]
            numbers = numbers.split(",")
            for i in range(len(numbers)):
                numbers[i] = int(numbers[i])
            random_list = numbers
        except:
            print2log("WARNING: QRNG site isn't responding. Probably Australia is on fire again :( Fallback to pseudo-random...")
            quantum = False

    if not quantum:
        for i in range(rep_num):
            random_list.append(random.randrange(max_num))
            
    return random_list

def retrieve_random_song(user_tag=""):
    global last_tag_albums, SCROLL_TIME, DEFAULT_TAG_INPUTFIELD_MESSAGE, PATH_CHROMEDRIVE, mixer_is_paused

    # var used to try to debug why sometimes it retrive only one song for multitracks releases
    its_only_a_single_track = False

    if user_tag in ["", DEFAULT_TAG_INPUTFIELD_MESSAGE]:
        print2log("-- RETRIEVE RANDOM SONG --")

        artists_per_page = 492

        # Find the last page
        page = requests.get("http://bandcamp.com/artist_index")
        update_bar(2)
        soup = BeautifulSoup(page.content, 'html.parser')

        # get last page (in buttons at bottom of the page)
        lastPage = int(soup.findAll("a", {"class": "pagenum"})[-1].string)

        # generates random numbers
        # its a list to reduce the numer of calls to the number generating page
        log.update("Have patience...\nRetrieving random numbers...")
        update_bar(3)
        list_of_random_numbers = generate_random_numbers(toggle_quantum)

        log.update(f"Have patience...\nThere are more than {artists_per_page * lastPage-artists_per_page} artists!")

        # Navigate to random artist index page and grab html
        # TODO: check if this *actually* grabs the last page
        randomPageNum = list_of_random_numbers[0] % lastPage

        artistIndexUrl = "http://bandcamp.com/artist_index?page=" + str(randomPageNum)
        page = requests.get(artistIndexUrl)
        window.refresh()
        soup = BeautifulSoup(page.content, 'html.parser')
        window.refresh()
        # get total of artits on page and grab one random
        artistList = soup.findAll("li", {"class": "item"})
        numOfArtists = len(artistList)

        # TODO: check if this *actually* grabs the last page
        randomArtistNum = (list_of_random_numbers[1] % numOfArtists)
        randomArtistPage = artistList[randomArtistNum].a.get('href')
        # check if there are more releases
        randomArtistPage += "/music"      
        print2log(f"randomArtistPage: {randomArtistPage}")


        # Navigate to artist index page and grab html
        page = requests.get(randomArtistPage)
        soup = BeautifulSoup(page.content, 'html.parser')
        update_bar(4)
        # grab artist name
        artist_name = soup.find('p', attrs={'id': 'band-name-location'})
        artist_name = artist_name.find('span', attrs={'class': 'title'})
        artist_name = artist_name.text
        print2log(f"artist_name: {artist_name}")
        log.update(f"Have patience...\nFound Artist: {artist_name}")
        # grab a random release
        try:
            music_grid = soup.find("ol", {"id": "music-grid"})
            links_to_music = music_grid.findAll("a")
            # select a random release and generate link
            randomReleaseNumber = list_of_random_numbers[2] % len(links_to_music)
            link_to_release = links_to_music[randomReleaseNumber].get("href")

            if link_to_release.split("/")[1] == "track":
                its_only_a_single_track = True

            link_to_release = randomArtistPage.replace(
                "/music", "") + link_to_release
        except:
            # artists has a single release as his homepage
            link_to_release = randomArtistPage
    else:
        print2log(f"-- RETRIEVE RANDOM SONG BY TAG: {user_tag} --")

        user_tag = user_tag.replace(" ", "-")

        links_to_music = []
        if last_tag_albums[0] == user_tag:
            links_to_music = last_tag_albums[1]
        else: #its a search with new tag

            #get path to chromedriver
            #TODO: grab from config.ini
            window.refresh()
            chromedriver_PATH = os.path.join(PATH_CHROMEDRIVE,'chromedriver.exe')
            # options for driver. start headless
            options = webdriver.ChromeOptions()
            options.add_argument('headless')
            options.add_argument('window-size=1200x600') # optional
            
            # HACKS for removing the console window that pop us when running a .exe compiled by pyinstaller
            options.add_experimental_option('excludeSwitches', ['enable-logging']) # remove console log when runned by .exe
            # https://stackoverflow.com/questions/52643556/getting-rid-of-chromedirver-console-window-with-pyinstaller/52644136
            # IMPORTAT! This made the trick! The file service.py in C:\Users\Username\AppData\Local\Programs\Python\Python38\Lib\site-packages\selenium\webdriver\common
            # chage: self.process = subprocess.Popen(cmd, env=self.env, close_fds=platform.system() != 'Windows', stdout=self.log_file, stderr=self.log_file, stdin=PIPE)
            # to: self.process = subprocess.Popen(cmd, stdin=PIPE, stdout=PIPE ,stderr=PIPE, shell=False, creationflags=0x08000000)

            # start driver
            window.refresh()
            driver = webdriver.Chrome(executable_path=chromedriver_PATH, options=options)
            # Load tag page and click view-more button to view all results
            driver.get(f"https://bandcamp.com/tag/{user_tag}?tab=all_releases")
            window.refresh()

            try: # to click button to see more items and start scrolling.
                window.refresh()
                driver.find_element_by_class_name("view-more").click()
                window.refresh()
                # Keep reloading and pausing to reach the bottom
                scroll_down_time = time.time() + SCROLL_TIME #set the number of times to reload
                pause = 0.25 #initial time interval between reloads
                while time.time() < scroll_down_time:
                    srapping_time = scroll_down_time - time.time()
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

                    log.update(f"Going deep...\nSpelunking time left: {round(srapping_time, 1)}")
                    window.refresh()
                    time.sleep(0.15) #faster reloads are kinda pointless
                # Otra manera sacada de aca, pero no logro hacerla andar mas rapido... Pero 'asegura' llegar al final si va a dos por hora
                # https://stackoverflow.com/questions/28928068/scroll-down-to-bottom-of-infinite-page-with-phantomjs-in-python
                # lenOfPage = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);var lenOfPage=document.body.scrollHeight;return lenOfPage;")
                # match=False
                # realod_number = 0
                # while(match==False):
                #     realod_number += 1
                #     lastCount = lenOfPage
                    
                #     driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                #     time.sleep(3) # hay que asegurarse que cargue la pagina...
                #     print(str(realod_number))
                #     lenOfPage = driver.execute_script("var lenOfPage=document.body.scrollHeight;return lenOfPage");
                #     if lastCount==lenOfPage:
                #         match=True
            except:
                # there to few items or none albumbs at all, so the 'view-more' button does not exist
                pass


                # grab html from driver
            html = driver.page_source
            # close driver's window and quit the driver
            driver.close()
            driver.quit()
            window.refresh()
            # grab links of all loaded albums
            soup = BeautifulSoup(html, 'html.parser')
            a_elements = soup.findAll("a", {"target": "_blank", "data-bind":"attr: {'href': tralbumUrl}, click: $parent.stat.bind(null, 'tralbum_click')"})
            links_to_music = []
            for a in a_elements:
                window.refresh()
                link = a.get("href")
                link = link.split("?")[0]
                links_to_music.append(link)

            if len(links_to_music) <= 0:
                print2log(f"!!!ERROR!!! There are no album with this tag: {user_tag}")
                return False, "", "", "", 0 

            #save tag and this new list, so it can ve retrived faster next time
            last_tag_albums = [user_tag, links_to_music]
        # ----

        # generates random numbers
        log.update("Have patience...\nRetrieving random numbers...")
        update_bar(5)
        list_of_random_numbers = generate_random_numbers(toggle_quantum)

        # select a random link from the link list
        randomReleaseNumber = list_of_random_numbers[2] % len(links_to_music)
        link_to_release = links_to_music[randomReleaseNumber]

        if link_to_release.split("/")[1] == "track":
                its_only_a_single_track = True

        print2log(f"len(links_to_music): {len(links_to_music)}")
        print2log(f"link_to_release: {link_to_release}")    

    
        
    print2log("link_to_release: " + link_to_release)
    update_bar(6)
    # -----------------------------------------------------------------------------
    # already have release link
    # -----------------------------------------------------------------------------

    # go to release page
    page = requests.get(link_to_release)
    update_bar(7)
    soup = BeautifulSoup(page.content, 'html.parser')
    # grab artist name and album name
    artist_name = soup.find('meta', attrs={'name': 'title'})
    artist_name = artist_name.get("content")
    album_name, artist_name = artist_name.split(", by ")
    artist_name = clean_string(artist_name)
    album_name = clean_string(album_name)
    # grab cover
    log.update(f"Have patience...\nGrabing cover art...")
    albumart = soup.findAll('div', attrs={'id': 'tralbumArt'})[0]
    albumart = albumart.findAll('img')[0]
    albumart_url = albumart.get("src")
    try:
        # ask for image
        im = requests.get(albumart_url).content
        # transform requested pic as a PIL Image
        im = Image.open(BytesIO(im))
    except:
        print2log("COVER GRABBING FAIL: "+albumart_url)
    else:
        im = im.convert('RGB')
        im = im.resize((300, 300))
        im.save("cover.png")
    update_bar(8)

    # grab data for tracks (mp3 file and title are in javascript)
    scripts = soup.findAll('script', type="text/javascript")

    for script in scripts:
        # lol, doble cast. better safe than sorry
        script_as_string = str(script.string)

        tracks_info = re.findall(r"trackinfo:(.*?)\],", script_as_string)
        if len(tracks_info) > 0: # safe check. Some scripts don't have trackinfo.
            tracks_info = tracks_info[0]

            tracks_file = re.findall(r"\"file\":(.*?),", tracks_info)
            tracks_title = re.findall(r"\"title\":\"(.*?)\",", tracks_info)
            tracks_duration = re.findall(r"\"duration\":(.*?),", tracks_info)


            if not its_only_a_single_track and len(tracks_title) == 1:
                # TODO: this happens time to time
                print2log(f"!!!WARNING!!!: only one track retrived, from a multitrack release: {link_to_release}")

            available_tracks_data = []

            for i, file in enumerate(tracks_file):
                if file == "null":
                    pass
                else:
                    # {"mp3-128":"https://t4.bcbits.com/stream/2ca2dd116679f13a60b3b1a7060f388b/mp3-128/2809292185?p=0&ts=1598108756&t=b80c4e8b8138b337a682c6681b9ec24e1b8a7f1e&token=1598108756_c563b569a2834cced9b91b6226e9dce11e1de430"}
                    file = file.split(":", 1)[1]
                    file = file[1:-2]

                    available_tracks_data.append([i, tracks_title[i], float(tracks_duration[i]), file])

            print2log(f"available_tracks len: {len(available_tracks_data)}")

            if len(available_tracks_data) <= 0:
                print2log("-------------------------------------------------------")
                print2log("WARNING!!!!!!!: There aren't any playeable track!")
                print2log("-------------------------------------------------------")
                print2log("There weren't any playable track in this album! :(\nLet's go again...")

                log.update(f"There weren't any playable track in this album! :( // Let's go again...")
                update_bar(9)
                time.sleep(1)
                retrieve_random_song(user_tag)


            # choose one track at random and download
            random_track_number = list_of_random_numbers[3] % len(available_tracks_data)
            selected_track = available_tracks_data[random_track_number]
            track_number = selected_track[0]
            track_name = selected_track[1]
            track_duration = selected_track[2] # in seconds 
            track_mp3 = selected_track[3] 

            # if is the release is a compilation, try to grab proper names
            if artist_name.lower() in ["various artists", "various", "v/a", "v.a.", "va"]:
                posible_separators = [" - ", " — "]
                separator_found = False
                for separator in posible_separators:                    
                    if separator in track_name:
                        split_name = track_name.split(separator, 1)
                        if split_name[0] not in [None, "", " "]:
                            artist_name = split_name[0]
                        if split_name[1] not in [None, "", " "]:
                            track_name = split_name[1]
                        separator_found = True
                        break
                if not separator_found:
                    #have in mind that are tracks that don;t have separator, even in a multi artists release
                    # https://boguscollective.bandcamp.com/album/b-o-g-u-s-collective-volume-1
                    print2log(f"REPORT THIS: '{track_name}' has no separator indentified!")

            print2log(f"DOWNLOADING: '{artist_name} - {track_name}.mp3'")
            log.update(f"Have patience...\nDownloading track...")

            # HACK: load a dummy file, so "track.mp3" gets unloaded from the mixer, and so I can write the new track into it.
            # mmm looks like it keeps loaden on memory tho
            # In pygame 2.0 there will be a function for this: https://www.pygame.org/docs/ref/music.html#pygame.mixer.music.unload
            mixer.music.load("dummy.mp3")

            update_bar(9)
            doc = requests.get(track_mp3)
            with open("track.mp3", 'wb') as f:
                f.write(doc.content)

            # WARNING: maybe this is bad idea if I am scrapping other things on scripts other that only tracks
            # already found the script with the data, so break out of the loop
            break

    update_bar(10)
    #reset pause button
    mixer_is_paused = False
    mixer.music.unpause()
    window['-BTN_PAUSE-'].update("PAUSE")
    #play new track
    print2log(f"PLAYING: {track_name} by {artist_name} // time:{track_duration}")
    mixer.music.load("track.mp3")
    mixer.music.play()

    return True, artist_name, track_name, link_to_release, track_duration


def download_albums(user_links="https://fatherjohnmisty.bandcamp.com/album/anthem-3-2"):
    global PATH_DOWNLOADS

    print2log("-- DOWNLOAD ALBUMS --")

    log_download.update(f"Starting to download\nHave patience...")
    window.refresh()

    # grab html
    urls = user_links.split("\n")

    for url in urls:
        if url in ['', " ", '\n']:
            continue

        print2log(f"url: {url}")
        log_download.update(f"Have patience...\nRetrieving from {url}")
        window.refresh()

        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')

        DOWNLOADS_PATH = PATH_DOWNLOADS
        
        # grab artist name and album name
        artist_name = soup.find('meta', attrs={'name': 'title'})
        artist_name = artist_name.get("content")
        album_name, artist_name = artist_name.split(", by ")
        is_a_multiartist_release = False
        if artist_name.lower() in ["various artists", "various", "v/a", "v.a.", "va"]:
            is_a_multiartist_release = True

        artist_name = clean_string(artist_name)
        album_name = clean_string(album_name)
        print2log(f"DOWNLOADING ALBUM: {album_name} by {artist_name}")
        log_download.update(f"DOWNLOADING ALBUM: {album_name} by {artist_name}\nhola")
        window.refresh()

        

        #create folder
        ALBUM_PATH = os.path.join(DOWNLOADS_PATH, f"{artist_name} - {album_name}") 
        os.mkdir(ALBUM_PATH)

        # grab cover
        albumart = soup.findAll('div', attrs={'id': 'tralbumArt'})[0]
        albumart = albumart.findAll('img')[0]
        albumart_url = albumart.get("src")
        log_download.update(f"DOWNLOADING ALBUM: {album_name} by {artist_name}\nGrabing cover art...")
        window.refresh()
        try:
            # ask for image
            im = requests.get(albumart_url).content
            # transform requested pic as a PIL Image
            im = Image.open(BytesIO(im))
        except:
            print2log("COVER GRABBING FAIL: "+albumart_url)
        else:
            im = im.convert('RGB')
            im.save(os.path.join(ALBUM_PATH, "cover.jpg"))

        # grab data for tracks (mp3 file and title are in javascript)
        scripts = soup.findAll('script', type="text/javascript")

        for script in scripts:
            # lol, doble cast. better safe than sorry
            script_as_string = str(script.string)

            tracks_info = re.findall(r"trackinfo:(.*?)\],", script_as_string)
            if len(tracks_info) > 0:
                tracks_info = tracks_info[0]  # grab the first. TODO: why not to use find() then?

                tracks_mp3 = re.findall(r"\"mp3-128\":\"(.*?)\"\},", tracks_info)
                tracks_title = re.findall(r"\"title\":\"(.*?)\",", tracks_info)

                # download all tracks
                for i, track_url in enumerate(tracks_mp3):
                    track_name = tracks_title[i]
                    print2log(f"DOWNLOADING TRACK {i+1} of {len(tracks_mp3)}")

                    if is_a_multiartist_release:
                        posible_separators = [" - ", " — "]
                        separator_found = False
                        for separator in posible_separators:                    
                            if separator in track_name:
                                split_name = track_name.split(separator, 1)
                                if split_name[0] not in [None, "", " "]:
                                    artist_name = split_name[0]
                                if split_name[1] not in [None, "", " "]:
                                    track_name = split_name[1]
                                separator_found = True
                                break
                        if not separator_found:
                            #have in mind that are tracks that don;t have separator, even in a multi artists release
                            # https://boguscollective.bandcamp.com/album/b-o-g-u-s-collective-volume-1
                            print2log(f"REPORT THIS: '{track_name}' has no separator indentified!")

                    # These can come ugly, clean again, becouse these are going to ve used on the writing of the file .
                    # the ungly ones, are keeped to be used on the file metatags
                    artist_name_clean = clean_string(artist_name)
                    track_name_clean = clean_string(track_name)
                    
                    log_download.update(f"DOWNLOADING ALBUM: {album_name}\nDownloaing track {i+1} of {len(tracks_mp3)}...")
                    window.refresh()

                    doc = requests.get(track_url)
                    # print2log(f"artist_name: {artist_name}\ntrack_name: {track_name}")
                    MP3_PATH = os.path.join(ALBUM_PATH, f"{artist_name_clean} - {track_name_clean}.mp3")
                    
                    with open(MP3_PATH, 'wb') as file:
                        file.write(doc.content)

                    # tags mp3
                    try:
                        metatag = mutagen.easyid3.EasyID3(MP3_PATH)
                    except mutagen.id3.ID3NoHeaderError:
                        metatag = mutagen.File(MP3_PATH, easy=True)
                        metatag.add_tags()
                    metatag['title'] = track_name
                    metatag['artist'] = artist_name
                    metatag['album'] = album_name
                    metatag['tracknumber'] = str(i+1)
                    metatag.save()
                        
                # WARNING: maybe this is bad idea if I am scrapping other things on scripts other that only tracks
                # already found the script with the data, so break out of the loop
                break
    print2log("DONE DOWNLOADING ALBUMS")
    log_download.update(f"DONE DOWNLOADING ALBUMS!\n♡")
    window.refresh()


def generate_menu():
    on = "☑"
    off = "☐"
    key_quantum = f'{on} Quantum::-MENU_QUANTUM-' if toggle_quantum else f'{off} Quantum::-MENU_QUANTUM-'
    key_scrobble = f'{on} Scrobble::-MENU_SCROBBLE-' if toggle_scrobble else f'{off} Scrobble::-MENU_SCROBBLE-'
    key_autoplay = f'{on} Autoplay::-MENU_AUTOPLAY-' if toggle_autoplay else f'{off} Autoplay::-MENU_AUTOPLAY-'
    temp_list = [
                ['Modes', ['Bandonaut::-MENU_RANDOM-', 'Downloader::-MENU_DOWNLOADER-', '---','Exit']],
                ['Pref', [key_scrobble, key_autoplay, key_quantum, '---','Open config.ini::-MENU_CONFIG-']],
                ['Help', ['About::-MENU_ABOUT-', '---','Open ReadMe::-MENU_HELP-']]
                ]      
    return temp_list

def next_random_track(user_tag=""):
    global music_artist, music_title, music_url, music_duration, song_started_at, already_scrobbled
    already_scrobbled = False
    window['-LOG_RANDOM-'].update("Have patience...\nStarting randonautic shenanigans...")
    update_bar(1)
    retrived_something, music_artist, music_title, music_url, music_duration = retrieve_random_song(user_tag)
    
    if retrived_something:
        window['-COVER-'].update("cover.png")
        window['-LOG_RANDOM-'].update(f"{music_title}\nby {music_artist}")
        window['-BTN_RANDOM-'].update("NEXT")
        # reset bar
        song_started_at = time.time()
    else:
        window['-LOG_RANDOM-'].update(f"There aren't any track with that tag! :(\nTry other tag or no tag at all")
        window['-BTN_RANDOM-'].update("START")
        # reset bar
    update_bar(0)

# ---------------------------------------------------
last_tag_albums = ["", []]
debuglog = ""

#------------------------------------------------------------------------------
mixer.init()
#------------------------------------------------------------------------------
sg.theme('Dark')
sg.set_options(element_padding=(0, 0))

COLOR_ALPHA = "#000000"
COLOR_0 = "#1c1e1f"
COLOR_1 = "#40514e"
COLOR_1 = "#2e2c38"
COLOR_2 = "#10999e"
COLOR_3 = "#31e3ca"
COLOR_4 = "#e4f9f5"
FONT_DEFAULT = ("Consolas", 10)

sg.LOOK_AND_FEEL_TABLE['Topanga_Dark'] = {'BACKGROUND': COLOR_0, 'TEXT': COLOR_3, 'INPUT': COLOR_1,
                      'SCROLL': COLOR_3, 'TOOLTIP_BACKGROUND_COLOR' : COLOR_1, 'TEXT_INPUT': COLOR_4, 'BUTTON': (COLOR_1, COLOR_3),
                      'PROGRESS': COLOR_0, 'SCROLL': COLOR_0, 'BORDER': 0.7, 'SLIDER_DEPTH':10, 'PROGRESS_DEPTH':0.1}
sg.ChangeLookAndFeel('Topanga_Dark')

# --------------------------------------
#OPTIONS
toggle_quantum = True
toggle_scrobble = False
toggle_autoplay = True
LASTFM_USERNAME = ""
LASTFM_PASSWORD = ""
WINDOW_POSITION = [100, 100]
SCROLL_TIME = 30
PATH_DOWNLOADS = os.getcwd()
PATH_CHROMEDRIVE = os.getcwd()

# check if a config.ini exist and grab preferences from there, if not create one
if os.path.isfile('config.ini'):
    #grab preferences from file
    with open("config.ini", 'r', encoding='utf-8') as config:
        for line in config:

            line = line.replace("\n", "")
            if "=" in line:
                key, value = line.split("=", 1)
            else:
                continue

            if key == "LASTFM_USERNAME" and value != "your_lastfm_username":
                LASTFM_USERNAME = value
            elif key == "LASTFM_PASSWORD" and value != "your_lastfm_password":
                LASTFM_PASSWORD = value
            elif key == "SCROLL_TIME":
                SCROLL_TIME = int(value)
            elif key == "ENABLE_AUTOPLAY":
                toggle_autoplay = True if value == "1" else False
            elif key == "ENABLE_SCROBBLE":
                toggle_scrobble = True if value == "1" else False
            elif key == "ENABLE_QUANTUM":
                toggle_quantum = True if value == "1" else False
            elif key == "WINDOW_X":
                WINDOW_POSITION[0] = int(value)
            elif key == "WINDOW_Y":
                WINDOW_POSITION[1] = int(value)
            elif key == "PATH_DOWNLOADS":
                PATH_DOWNLOADS = value
            elif key == "PATH_CHROMEDRIVE":
                PATH_CHROMEDRIVE = value
else:
    defaul_config = """ENABLE_SCROBBLE=0
LASTFM_USERNAME=your_lastfm_username
LASTFM_PASSWORD=your_lastfm_password
SCROLL_TIME=10
ENABLE_AUTOPLAY=1
ENABLE_QUANTUM=1
PATH_DOWNLOADS=
PATH_CHROMEDRIVE="""
    with open("config.ini", 'w', encoding='utf-8') as config:
        config.write(defaul_config)  
# -----------------

window_menu = sg.Menu(generate_menu())

DEFAULT_TAG_INPUTFIELD_MESSAGE = "tag filter"
layout_random = [
            [sg.Image(filename="main.png", key='-COVER-', size=(300, 300))],
            [sg.ProgressBar(10, orientation='h', size=(27.7,4), key='-BAR-', border_width=0)],
            [sg.Text('', font=("Consolas", 2))],
            [sg.Input(DEFAULT_TAG_INPUTFIELD_MESSAGE, key='-TAG-', size=(43,4), border_width=0, justification='c')],
            [sg.Text('\n ⬇ press START button to bandonaut!', key='-LOG_RANDOM-', size=(43, 2), justification='left', font=FONT_DEFAULT,pad=(0, 8))],
            [
            sg.Button('START', key='-BTN_RANDOM-'),
            sg.Button('PAUSE', key='-BTN_PAUSE-'),
            sg.Button('URL', key='-BTN_LINK-')
            ],
        ]

layout_downloader = [
            [sg.Multiline("", change_submits=True, key='-INPUT_LINKS-', autoscroll=False, enter_submits=False, size=(70, 15), border_width=0)],
            [sg.Text('', justification='left', font=("Consolas", 3))],
            [sg.Text('add albums to download. one URL per line. invalid URLs will crash it', key='-LOG_DOWNLOAD-', size=(70, 2), justification='c', font=FONT_DEFAULT)],
            [sg.Text('', justification='left', font=("Consolas", 3))],
            [sg.Button('DOWNLOAD', key='-BTN_DOWNLOAD-')],
            [sg.Text('', justification='left', font=("Consolas", 3))]
        ]

layout = [[window_menu],[sg.Column(layout_random, key='-COL_RANDOM-', element_justification='r'), sg.Column(layout_downloader, visible=False, key='-COL_DOWNLOAD-', element_justification='c')]]

window = sg.Window("BANDONAUTICA",
                   layout,
                   finalize = True, #for some reason this needs to be called before accesing the raw tkinter widgets
                   # keep_on_top = True,
                   # grab_anywhere=True,
                   # no_titlebar=True,
                   location=(WINDOW_POSITION[0],WINDOW_POSITION[1]),
                   # transparent_color=sg.theme_background_color(), 
                   default_element_size=(12, 1),
                   use_default_focus=False, # para que no le de el punteado feo a los botones apenas arranca
                   auto_size_buttons=False,
                   default_button_element_size=(12, 1),
                   icon='icon.ico',
                   return_keyboard_events=True # ENTER devuelve '\r' 
                   )


progress_bar = window.FindElement('-BAR-')
progress_bar.Widget.configure(length=300) #hardcode bar length https://www.gitmemory.com/issue/PySimpleGUI/PySimpleGUI/2651/601406486
log = window.FindElement('-LOG_RANDOM-')
log_download = window.FindElement('-LOG_DOWNLOAD-')
# change cursor type on over. with hack to acceses the raw tkinter widgets 
# https://www.tcl.tk/man/tcl8.4/TkCmd/cursors.htm
# window.FindElement("-COVER-").Widget.config(cursor="fleur") #only makes sence when grab_anywhere is true
window.FindElement("-BTN_RANDOM-").Widget.config(cursor="hand2")
window.FindElement("-BTN_PAUSE-").Widget.config(cursor="hand2")
window.FindElement("-BTN_LINK-").Widget.config(cursor="hand2")
window.FindElement("-BTN_DOWNLOAD-").Widget.config(cursor="hand2")

window['-TAG-'].Widget.config(insertbackground=COLOR_4)
window['-INPUT_LINKS-'].Widget.config(insertbackground=COLOR_4)

mixer_is_paused = False
music_artist = ""
music_title = ""
music_url = ""
music_duration = 0
song_started_at = 0
pause_started_at = 0
already_scrobbled = False


def main():
    global toggle_quantum
    global toggle_scrobble
    global toggle_autoplay
    global LASTFM_USERNAME
    global LASTFM_PASSWORD
    global SCROLL_TIME
    global mixer_is_paused
    global music_artist
    global music_title
    global music_url
    global music_duration
    global song_started_at
    global pause_started_at
    global already_scrobbled

    MODE_RANDOM = 1
    MODE_DOWNLOADER = 0
    MODE_CURRENT = MODE_RANDOM

    while True:
        event, values = window.read(timeout=500)
        if event in (sg.WIN_CLOSED, 'Exit'):
            break
        elif event == '\r':
            if MODE_CURRENT == MODE_RANDOM:
                next_random_track(values['-TAG-'])
        elif event == '-BTN_RANDOM-':
            next_random_track(values['-TAG-'])
        elif event == '-BTN_PAUSE-':
            if mixer_is_paused:
                mixer_is_paused = False
                mixer.music.unpause()
                window['-BTN_PAUSE-'].update("PAUSE")
                song_started_at = song_started_at + (time.time() - pause_started_at)
            else:
                mixer_is_paused = True
                mixer.music.pause()
                window['-BTN_PAUSE-'].update("RESUME")
                pause_started_at = time.time()
                print(f"played_time {time.time() - song_started_at}")
        elif event == '-BTN_LINK-':
            if music_url != "":
                webbrowser.open(music_url)
        elif event == '-BTN_DOWNLOAD-':
            download_albums(values['-INPUT_LINKS-'])
        else:
            if "::" in event:
                menu_entry_key = event.split("::")[1]
                if menu_entry_key == '-MENU_RANDOM-':
                    MODE_CURRENT = MODE_RANDOM
                    window[f'-COL_RANDOM-'].update(visible=True)
                    window[f'-COL_DOWNLOAD-'].update(visible=False)
                elif menu_entry_key == '-MENU_DOWNLOADER-':
                    MODE_CURRENT = MODE_DOWNLOADER
                    window[f'-COL_RANDOM-'].update(visible=False)
                    window[f'-COL_DOWNLOAD-'].update(visible=True)
                elif menu_entry_key == '-MENU_CONFIG-':
                    os.system("config.ini")
                elif menu_entry_key == '-MENU_HELP-':
                    os.system("README.txt")
                elif menu_entry_key == '-MENU_ABOUT-':
                    # button_type=5 removes the horrendous OK button
                    sg.Popup('Bandonautica v1.01\nby bembi & lemu',button_type=5)
                elif menu_entry_key == '-MENU_QUANTUM-':
                    toggle_quantum = not toggle_quantum
                    temp_menu = generate_menu()
                    window_menu.Update(temp_menu)
                elif menu_entry_key == '-MENU_AUTOPLAY-':
                    toggle_autoplay = not toggle_autoplay
                    temp_menu = generate_menu()
                    window_menu.Update(temp_menu)
                elif menu_entry_key == '-MENU_SCROBBLE-':
                    toggle_scrobble = not toggle_scrobble
                    temp_menu = generate_menu()
                    window_menu.Update(temp_menu)

                    if toggle_scrobble and LASTFM_USERNAME == "":
                        toggle_scrobble = False
                        print2log("There are no LASTFM credentials on config.ini")

        if music_artist != "":
            if mixer_is_paused:
                pass
            else:
                played_time = time.time() - song_started_at
                if played_time > music_duration:
                    if toggle_autoplay:
                        next_random_track(values['-TAG-'])
                elif played_time > (music_duration*0.75):
                    if toggle_scrobble and not already_scrobbled and music_duration != 0:
                        
                        already_scrobbled = True
                        print2log(f"SCROBBLING: {music_title} by {music_artist}")                 
                        scrobble_track(music_artist, music_title)

if __name__ == "__main__":
    try:
        with open("log.txt", "w", encoding='utf-8') as logfile:
            logfile.write("")
        main()
    except Exception as e:
        debuglog += str(e)
        print(e)
    finally:
        with open("log.txt", "w", encoding='utf-8') as logfile:
            logfile.write(debuglog)
