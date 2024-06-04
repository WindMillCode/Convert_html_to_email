
def local_deps():
  import sys
  if sys.platform == 'win32':
    sys.path.append(sys.path[0] + '.\\site-packages\\windows')
  elif sys.platform =='linux':
    sys.path.append(sys.path[0] + './site-packages/linux')
local_deps()
import re
from bs4 import BeautifulSoup
import urllib.request as urllib2
from urllib.parse import urljoin
from optparse import OptionParser
import logging
import base64

from threading import Thread

def apply_predicate_to_image_urls(src):
  return "https://firebasestorage.googleapis.com/v0/b/eneobia.appspot.com/o/emails%2Ftemplate_0%2F{}?alt=media".format(src.split("images/")[1])

def url_can_be_converted(tag):
  return tag.name.lower() == "img" and tag.has_attr('src') and not re.match('^data:', tag['src'])

def background_img_can_be_converted(tag):
  return re.search(r'url\((?!["\']?data:)', tag.get('style', ''))

def fetch_image(url, link, options):
  if options.turn_to_data_urls.upper() == 'YES':
    image = urllib2.urlopen(url).read()
    encoded = base64.b64encode(image).decode('utf-8')
    logging.debug("base64 encoded image " + encoded)
    link['src'] = "data:image/png;base64," + encoded
  elif options.use_predicate_on_image_urls.upper() == 'YES':
    link['src'] = apply_predicate_to_image_urls(url)

def fetch_background_image(url, tag, options):
  if options.turn_to_data_urls.upper() == 'YES':
    image = urllib2.urlopen(url).read()
    encoded = base64.b64encode(image).decode('utf-8')
    logging.debug("base64 encoded background image " + encoded)
    new_style = re.sub(r'url\([\'"]?(.*?)[\'"]?\)', 'url("data:image/png;base64,' + encoded + '")', tag['style'])
    tag['style'] = new_style
  elif options.use_predicate_on_image_urls.upper() == 'YES':
    new_style = re.sub(r'url\([\'"]?(.*?)[\'"]?\)', 'url("' + apply_predicate_to_image_urls(url) + '")', tag['style'])
    tag['style'] = new_style

def replace_braces(content):
  content = re.sub(r'{', '{{', content)
  content = re.sub(r'}', '}}', content)
  return content



if __name__ == "__main__":
  usage = "usage: %prog http://www.server.com/page.html"
  parser = OptionParser(usage=usage,
    description="Convert all external images to data urls")
  parser.add_option("-d", "--debug", action="store_true", dest="debug",
    help="Turn on debug logging, prints base64 encoded images")
  parser.add_option("-q", "--quiet", action="store_true", dest="quiet",
    help="turn off all logging")
  parser.add_option("-o", "--output", action="store", dest="output",
    default="output.html",
    help="output file name, defaults to output.html")
  parser.add_option("-t", "--turn-to-data-urls", action="store", dest="turn_to_data_urls",
    default="NO",
    help="turns all images with urls to data urls")
  parser.add_option("-p", "--use-predicate-on-image-urls", action="store", dest="use_predicate_on_image_urls",
    default="YES",
    help="apples predicate to image urls")
  parser.add_option("-r", "--replace-braces", action="store", dest="replace_braces",
    default="YES",
    help="replace single braces with double")
  (options, args) = parser.parse_args()

  logging.basicConfig(level=logging.DEBUG if options.debug else
    (logging.ERROR if options.quiet else logging.INFO))

  for page_url in args:
    logging.info("Reading page " + page_url)
    page = urllib2.urlopen(page_url).read()
    logging.info("Page load complete, processing")

    soup = BeautifulSoup(page, 'html.parser')

    threads = []

    for link in soup.findAll(url_can_be_converted):
      image_url = urljoin(page_url, link['src'])
      logging.info("loading image " + image_url)

      thread = Thread(target=fetch_image, args=(image_url, link, options))
      threads.append(thread)
      thread.start()

    for tag in soup.findAll(background_img_can_be_converted):
      style = tag['style']
      url_match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
      if url_match:
        background_image_url = urljoin(page_url, url_match.group(1))
        logging.info("loading background image " + background_image_url)
        thread = Thread(target=fetch_background_image, args=(background_image_url, tag,options))
        threads.append(thread)
        thread.start()

      for thread in threads:
        thread.join()

    html = soup.prettify(formatter="html")
    output_filename = options.output
    logging.info("Writing results to " + output_filename)
    with open(output_filename, "w", encoding='utf-8') as file:
      if options.replace_braces.upper() == 'YES':
        html = replace_braces(html)
      file.write(html)



