import os
import json
import hashlib
import ppdeep
from jsondiff import diff
import re

class Fingerprint:

    def __init__(self,fp_raw:dict):
        self._raw = fp_raw['fp']['fingerprint']
        self._stable = fp_raw['creep']
        self.bothash = fp_raw['botHash']
        self.badbot = fp_raw['badBot']
        self._lies = {}
        for k,v in self._raw.items():
           if "$hash" in v.keys():
               v.pop("$hash")

           #self._raw[k] = v

           if "lied" in v.keys() and v["lied"] == True:
               self._lies[k] = v

        self._raw['LowerEntropy'] = fp_raw['fp']['LowerEntropy']
        self._raw['braveFingerprintingBlocking'] = fp_raw['fp']['braveFingerprintingBlocking']
        self._hashes = {}

        for k, v in self._raw.items():
            self._hashes[k] = ppdeep.hash(json.dumps(v,sort_keys=True).encode('utf-8'))

        fuzzy = ""
        for k, v in self._hashes.items():
            if k not in self._lies:
                fuzzy += v

        self._hashes['fuzzy'] = ppdeep.hash(fuzzy.encode('utf-8'))

        self._hashes['fp'] = hashlib.sha256(json.dumps(self._raw, sort_keys=True).encode('utf-8')).hexdigest()
        self._hashes['fp_lie_free'] = hashlib.sha256(
            json.dumps({k: v for k, v in self._raw.items() if k not in self._lies}, sort_keys=True).encode(
                'utf-8')).hexdigest()
        self._hashes['fp_stable'] = hashlib.sha256(json.dumps(self._stable, sort_keys=True).encode('utf-8')).hexdigest()

        self._meta = {}
        self.botPatterns = [
                # custom order is important
                "liedWorkerScope", # lws
                "liedPlatformVersion", # lpv
                "functionToStringHasProxy", # ftp
                "outsideFeaturesVersion", # ofv
                "extremeLieCount", # elc
                "excessiveLooseFingerprints", #elf(compute on server)
                "workerScopeIsBlocked", # wsb
                "crowdBlendingScoreIsLow" # csl
        ]

    def digest(self):
        return self._hashes['fp']

    def stable_digest(self):
        return self._hashes['fp_stable']

    '''def hardenEntropy(self, workerScope, prop):
        return (
            prop if not workerScope else
            prop if workerScope.get('localeEntropyIsTrusty') and workerScope.get('localeIntlEntropyIsTrusty') else
            None
        )

    def privacyResistFingerprinting(self):
        return self._raw.get('resistance') and re.match(r'^(tor browser|firefox)$', self._raw.get('resistance').get('privacy',""),
                                              re.IGNORECASE)

    def _get_brave_unprotected_parameters(self, parameters):
        blocked = set(['FRAGMENT_SHADER.HIGH_FLOAT.precision',
		'FRAGMENT_SHADER.HIGH_FLOAT.rangeMax',
		'FRAGMENT_SHADER.HIGH_FLOAT.rangeMin',
		'FRAGMENT_SHADER.HIGH_INT.precision',
		'FRAGMENT_SHADER.HIGH_INT.rangeMax',
		'FRAGMENT_SHADER.HIGH_INT.rangeMin',
		'FRAGMENT_SHADER.LOW_FLOAT.precision',
		'FRAGMENT_SHADER.LOW_FLOAT.rangeMax',
		'FRAGMENT_SHADER.LOW_FLOAT.rangeMin',
		'FRAGMENT_SHADER.MEDIUM_FLOAT.precision',
		'FRAGMENT_SHADER.MEDIUM_FLOAT.rangeMax',
		'FRAGMENT_SHADER.MEDIUM_FLOAT.rangeMin',
		'MAX_COMBINED_FRAGMENT_UNIFORM_COMPONENTS',
		'MAX_COMBINED_UNIFORM_BLOCKS',
		'MAX_COMBINED_VERTEX_UNIFORM_COMPONENTS',
		'MAX_DRAW_BUFFERS_WEBGL',
		'MAX_FRAGMENT_INPUT_COMPONENTS',
		'MAX_FRAGMENT_UNIFORM_BLOCKS',
		'MAX_FRAGMENT_UNIFORM_COMPONENTS',
		'MAX_TEXTURE_MAX_ANISOTROPY_EXT',
		'MAX_TRANSFORM_FEEDBACK_INTERLEAVED_COMPONENTS',
		'MAX_UNIFORM_BUFFER_BINDINGS',
		'MAX_VARYING_COMPONENTS',
		'MAX_VERTEX_OUTPUT_COMPONENTS',
		'MAX_VERTEX_UNIFORM_BLOCKS',
		'MAX_VERTEX_UNIFORM_COMPONENTS',
		'SHADING_LANGUAGE_VERSION',
		'UNMASKED_RENDERER_WEBGL',
		'UNMASKED_VENDOR_WEBGL',
		'VERSION',
		'VERTEX_SHADER.HIGH_FLOAT.precision',
		'VERTEX_SHADER.HIGH_FLOAT.rangeMax',
		'VERTEX_SHADER.HIGH_FLOAT.rangeMin',
		'VERTEX_SHADER.HIGH_INT.precision',
		'VERTEX_SHADER.HIGH_INT.rangeMax',
		'VERTEX_SHADER.HIGH_INT.rangeMin',
		'VERTEX_SHADER.LOW_FLOAT.precision',
		'VERTEX_SHADER.LOW_FLOAT.rangeMax',
		'VERTEX_SHADER.LOW_FLOAT.rangeMin',
		'VERTEX_SHADER.MEDIUM_FLOAT.precision',
		'VERTEX_SHADER.MEDIUM_FLOAT.rangeMax',
		'VERTEX_SHADER.MEDIUM_FLOAT.rangeMin',])

        safe_parameters = {k: v for k, v in parameters.items() if k not in blocked}
        return safe_parameters

    def _harden_gpu(self,canvas_webgl):
        gpu = canvas_webgl.get('gpu')
        confidence = gpu.get('confidence')
        compressed_gpu = gpu.get('compressedGPU')
        return (
            {} if confidence == 'low' else {
                'UNMASKED_RENDERER_WEBGL': compressed_gpu,
                'UNMASKED_VENDOR_WEBGL': canvas_webgl.get('parameters').get('UNMASKED_VENDOR_WEBGL'),
            }
        )

    def _get_canvas_webgl(self):
        canvas_webgl = self._raw.get('canvasWebgl')
        if not canvas_webgl or canvas_webgl.get('lied') or self._raw.get('LowerEntropy').get('WEBGL'):
            return None

        if self._raw.get('braveFingerprintingBlocking'):
            return {
                'parameters': {
                    **self._get_brave_unprotected_parameters(canvas_webgl.get('parameters')),
                    **self._harden_gpu(canvas_webgl),
                },
            }
        else:
            canvas2d = self._raw.get('canvas2d')
            if canvas2d and canvas2d.get('lied') or self._raw.get('LowerEntropy').get('CANVAS'):
                # distrust images
                gl = canvas_webgl
                extensions = gl.get('extensions')
                gpu = gl.get('gpu')
                lied = gl.get('lied')
                parameter_or_extension_lie = gl.get('parameterOrExtensionLie')
                return {
                    'extensions': extensions,
                    'gpu': gpu,
                    'lied': lied,
                    'parameterOrExtensionLie': parameter_or_extension_lie,
                }
            else:
                return canvas_webgl




    def stableFp(self):

        navigator = (
            None if self._raw.get('navigator') is None or self._raw.get('navigator').get('lied') else {
                'bluetoothAvailability': self._raw.get('navigator').get('bluetoothAvailability'),
                'device': self._raw.get('navigator').get('device'),
                'deviceMemory': self._raw.get('navigator').get('deviceMemory'),
                'hardwareConcurrency': self._raw.get('navigator').get('hardwareConcurrency'),
                'maxTouchPoints': self._raw.get('navigator').get('maxTouchPoints'),
                'oscpu': self._raw.get('navigator').get('oscpu'),
                'platform': self._raw.get('navigator').get('platform'),
                'system': self._raw.get('navigator').get('system'),
                'userAgentData': {
                    **(self._raw.get('navigator').get('userAgentData') or {}),
                    'brandsVersion': None,
                    'uaFullVersion': None,
                },
                'vendor': self._raw.get('navigator').get('vendor'),
            }
        )

        screen = (
            None if self._raw.get('screen') is None or self._raw.get('screen').get(
                'lied') or self.privacyResistFingerprinting() or self._raw.get('LowerEntropy').get('SCREEN') else
            self.hardenEntropy(
                self._raw.get('workerScope'), {
                    'height': self._raw.get('screen').get('height'),
                    'width': self._raw.get('screen').get('width'),
                    'pixelDepth': self._raw.get('screen').get('pixelDepth'),
                    'colorDepth': self._raw.get('screen').get('colorDepth'),
                    'lied': self._raw.get('screen').get('lied'),
                },
            )
        ),
        workerScope = (
            None if not self._raw.get('workerScope') or self._raw.get('workerScope').get('lied') else {
                'deviceMemory': (
                    None if self._raw.get('braveFingerprintingBlocking') else self._raw.get('workerScope').get('deviceMemory')
                ),
                'hardwareConcurrency': (
                    None if self._raw.get('braveFingerprintingBlocking') else self._raw.get('workerScope').get('hardwareConcurrency')
                ),
                'language': self._raw.get('workerScope').get('language') if not self._raw.get('LowerEntropy').get('TIME_ZONE') else None,
                'platform': self._raw.get('workerScope').get('platform'),
                'system': self._raw.get('workerScope').get('system'),
                'device': self._raw.get('workerScope').get('device'),
                'timezoneLocation': (
                    None if self._raw.get('LowerEntropy').get('TIME_ZONE') else self.hardenEntropy(self._raw.get('workerScope'),
                                                                      self._raw.get('workerScope').get('timezoneLocation'))
                ),
                'webglRenderer': (
                    self._raw.get('workerScope').get('gpu').get('compressedGPU') if self._raw.get('workerScope').get('gpu').get(
                        'confidence') != 'low' else None
                ),
                'webglVendor': (
                    self._raw.get('workerScope').get('webglVendor') if self._raw.get('workerScope').get('gpu').get(
                        'confidence') != 'low' else None
                ),
                'userAgentData': {
                    **(self._raw.get('workerScope').get('userAgentData') or {}),
                    'brandsVersion': None,
                    'uaFullVersion': None,
                },
            }
        )
        media = self._raw.get('media'),

        canvas2d = self._raw.get('canvas2d')
        if canvas2d:
            lied = canvas2d.get('lied')
            liedTextMetrics = canvas2d.get('liedTextMetrics')
            data = None
            if not lied:
                dataURI = canvas2d.get('dataURI')
                paintURI = canvas2d.get('paintURI')
                textURI = canvas2d.get('textURI')
                emojiURI = canvas2d.get('emojiURI')
                data = {
                    'lied': lied,
                    **{'dataURI': dataURI, 'paintURI': paintURI, 'textURI': textURI, 'emojiURI': emojiURI},
                }
            if not liedTextMetrics:
                textMetricsSystemSum = canvas2d.get('textMetricsSystemSum')
                emojiSet = canvas2d.get('emojiSet')
                data = {
                    **(data or {}),
                    **{'textMetricsSystemSum': textMetricsSystemSum, 'emojiSet': emojiSet},
                }
            canvas2d = data

        canvasWebgl = self._get_canvas_webgl()

        return navigator, screen, media, canvas2d, canvasWebgl, workerScope
        '''

def summarize(path:str):
    with open(path,"r") as f: reqmeta = json.load(f)
    #print(reqmeta)
    print("keys in reqmeta: ",reqmeta.keys())
    print("keys in reqmeta['fingerprint']: ",reqmeta['fingerprint'].keys())
    fp = Fingerprint(reqmeta['fingerprint'])
    print("your browser fingerprint: ",fp.digest())


def compare(fp1:Fingerprint,fp2:Fingerprint):
    print(fp1.stable_digest(), fp2.stable_digest())
    if fp1.digest() == fp2.digest():
        print("fingerprint match")
        print("your fp1 browser fingerprint: ",fp1.digest())
        print("your fp2 browser fingerprint: ",fp2.digest())
    else:
        print("fingerprint mismatch")
        print("your stable fp1 browser fingerprint: ",fp1._hashes['fuzzy'])
        print("your stable fp2 browser fingerprint: ",fp2._hashes['fuzzy'])
        score = ppdeep.compare(fp1._hashes['fuzzy'], fp2._hashes['fuzzy'])
        print("fuzzy score: ",score)

        keys = set(list(fp1._raw.keys()) + list(fp2._raw.keys()))
        for k in keys:
            if k in ['fp','fp_lie_free']: continue

            if k not in fp1._hashes.keys():
                print("fp1 missing key: ",k)
            elif k not in fp2._hashes.keys():
                print("fp2 missing key: ",k)
            else:
                score = ppdeep.compare(fp1._hashes[k],fp2._hashes[k])
                if score < 100:
                    print("key: ",k," mismatch, score: ",score)
                    x = diff(fp1._raw[k],fp2._raw[k])
                    print(x)
                else:
                    print("##### key: ",k," match, score: ",score)

def get_fp(path:str) -> Fingerprint:
    with open(path,"r") as f:
        reqmeta = json.load(f)
        return Fingerprint(reqmeta)

def bot_or_not(path:str):
    with open(path,"r") as f:
        reqmeta = json.load(f)
        fp = Fingerprint(reqmeta)
        print(fp.stable_digest())
        res = {}
        res['device'] = fp._raw['navigator']['device']
        res['browser'] = fp._raw['navigator']['userAgentParsed']
        res['browserPrivateMode'] = fp._raw['navigator'].get('doNotTrack',None)
        res['headlessRating'] = fp._raw['headless']['headlessRating']
        res['stealthRating'] = fp._raw['headless']['stealthRating']
        res['timezone'] = fp._raw['timezone']['zone']
        res['lies'] = fp._raw['lies']['totalLies']

        '''
        if fp._raw['lies']['totalLies'] > 7:
            res['isBot'] = True
            res['botType'] = fp._raw['resistance']['extension']
        elif fp._raw['headless']['likeHeadlessRating'] > 70 \
                or fp._raw['headless']['headlessRating'] > 20 \
                or fp._raw['headless']['stealthRating'] > 20:
            res['isBot'] = True
            res['botType'] = "headless"
        else:
            res['isBot'] = False
        '''
        if fp.badbot:
            print("bad bot")
            print(fp.badbot)

        print(res)

if __name__ == "__main__":
    #summarize("./safari_normal.json")
    #summarize("./safari_private.json")
    #summarize("./chrome_normal.json")
    #summarize("./safari_normal.json")
    #compare(get_fp("./safari_normal.json"),get_fp("./safari_private.json"))
    #compare(get_fp("./safari_normal.json"),get_fp("./chrome_normal.json"))
    #compare(get_fp("./chrome_normal.json"),get_fp("./chrome_private.json"))
    #compare(get_fp("./chrome_normal.json"),get_fp("./puppeteer.json"))
    #compare(get_fp("./chrome_normal.json"), get_fp("./puppeteer_stealth.json"))
    #bot_or_not("./chrome_normal_bothash.json")
    #compare(get_fp("./chrome_normal_bothash.json"), get_fp("./chrome_private_bothash.json"))
    #compare(get_fp("./chrome_normal_bothash.json"), get_fp("./safari_private_bothash.json"))
    for f in ("./chrome_normal_bothash.json","./chrome_private_bothash.json","./safari_private_bothash.json"):
        bot_or_not(f)
# ef3e3e9c263c65b665bc4083f4af4960e8717353de8b1bab8f1ebbf3887b5b78
# ef3e3e9c263c65b665bc4083f4af4960e8717353de8b1bab8f1ebbf3887b5b78
# f56e0de64e198a838757bcbce6c2a1ca8d45228f2c087627954ddc2b7f6be915