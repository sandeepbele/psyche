from playwright.sync_api import sync_playwright

def log_network_request(request):
    print(f"Network Request: {request.method} method called to URL {request.url}")

from playwright.sync_api import sync_playwright

from playwright.sync_api import sync_playwright

def log_console_message(msg):
    print(f"{msg.text}")

def log_response(response):
    request = response.request
    print(f"{request.method} on {request.url} with {response.status} {response.headers.get('content-type','unknown-content')} {response.headers.get('content-length', 'unknown-length')}")

def analyze_page(url):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537',
            ignore_https_errors=True
        )
        page = context.new_page()
        # Listen for responses to capture request details
        page.on("response", log_response)
        page.on("console", log_console_message)
        #page.on("request", log_network_request)

        js_to_inject = """
        // Example for Fetch API interception
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            console.log(`Fetch on ${args[0]} from function XYZ`);
            const response = await originalFetch(...args);
            console.log(`Fetch on ${args[0]} with ${response.status} ${response.headers.get('content-type')} ${response.headers.get('content-length')}`);
            return response;
        };

        // MutationObserver for DOM changes
       new MutationObserver(mutations => {
            mutations.forEach(mutation => {
                let message = '';
                switch (mutation.type) {
                    case 'childList':
                        if (mutation.addedNodes.length) {
                            const addedNodesNames = Array.from(mutation.addedNodes).map(node => node.nodeName).join(', ');
                            message = `Added nodes: ${addedNodesNames} to ${mutation.target.nodeName}.`;
                        }
                        if (mutation.removedNodes.length) {
                            const removedNodesNames = Array.from(mutation.removedNodes).map(node => node.nodeName).join(', ');
                            message += ` Removed nodes: ${removedNodesNames} from ${mutation.target.nodeName}.`;
                        }
                        break;
                    case 'attributes':
                        message = `Attribute ${mutation.attributeName} was modified in ${mutation.target.nodeName}.`;
                        break;
                    case 'characterData':
                        message = `Text content changed in ${mutation.target.nodeName}.`;
                        break;
                }
                console.log(mutation.type+":"+message);
            });
        }).observe(document.documentElement, { attributes: true, childList: true, subtree: true, characterData: true });

        """

        # Inject JavaScript for detailed DOM monitoring and function call logging
        #page.add_init_script(js_to_inject)

        page.goto(url)
        page.wait_for_load_state('domcontentloaded')  # Wait for the 'DOMContentLoaded' event
        page.evaluate(js_to_inject)
        page.wait_for_load_state('networkidle')

        input("Press Enter to finish...")  # Hold the script until user input for manual review

        browser.close()




#analyze_page('https://example.com')  # Replace with your target URL


#analyze_page('https://example.com')  # Replace with your target URL

#django management command
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Analyze a web page'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='The URL of the web page to analyze')

    def handle(self, *args, **kwargs):
        analyze_page(kwargs['url'])