import hashlib, json

class Fingerprint:

    def __init__(self,fp_raw:dict):
        if fp_raw is not None and fp_raw != {}:
            self._raw = fp_raw['fp']['fingerprint'].copy()
            self._stable = fp_raw['creep']
            self.bothash = fp_raw['botHash']
            self.badbot = fp_raw['badBot']
            self._lies = {}
            for k,v in self._raw.items():
               if "$hash" in v.keys():
                   v.pop("$hash")

               if "lied" in v.keys() and v["lied"] == True:
                   self._lies[k] = v

            self._raw['LowerEntropy'] = fp_raw['fp']['LowerEntropy']
            self._raw['braveFingerprintingBlocking'] = fp_raw['fp']['braveFingerprintingBlocking']
            self._hashes = {}

            '''for k, v in self._raw.items():
                self._hashes[k] = ppdeep.hash(json.dumps(v,sort_keys=True).encode('utf-8'))

            fuzzy = ""
            for k, v in self._hashes.items():
                if k not in self._lies:
                    fuzzy += v

            self._hashes['fuzzy'] = ppdeep.hash(fuzzy.encode('utf-8'))'''

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
    
    def is_bot(self):
        bot_hash_string = self.bothash
        bot_hash_number = int(bot_hash_string, 2)
        return bot_hash_number > 2 or \
            self.stealthRating() > 10 or \
            self.isWebDriverEnabled() or \
            self.headlessRating() > 60 or \
            self.lies() > 8 or \
            self.resistance() is not None
    
    def bot_type(self):
        reasons = []
        if self.badbot:
            reasons.append({"badbot": self.badbot, "botHash": self.bothash})
        if self.stealthRating() > 10:
            reasons.append({"stealthRating": self.stealthRating(), "stealth": self._raw['headless']['stealth']})
        if self.headlessRating() > 60:
            reasons.append({"headlessRating": self.headlessRating(), "headless": self._raw['headless']['headless']})
        if self.lies() > 8:
            reasons.append({"lies": self._raw['lies']})
        if self.resistance() is not None:
            reasons.append({"resistance": self._raw['resistance']})
        
        return reasons or None
    
    def device(self):
        return self._raw.get('navigator').get('device')

    def browser(self):
        return self._raw.get('navigator').get('userAgentParsed')

    def browserPrivateMode(self):
        return self._raw.get('navigator').get('doNotTrack')

    def isWebDriverEnabled(self):
        return self._raw.get('headless').get('webDriverIsOn')
    
    def headlessRating(self):
        return self._raw.get('headless').get('headlessRating')

    def stealthRating(self):
        return self._raw.get('headless').get('stealthRating')

    def timezone(self):
        tz_loc = self._raw.get('timezone').get('location')
        tz_zone = "/".join([w.strip().replace(" ","_") for w in tz_loc.split(',')]) if tz_loc else None
        return tz_zone
    
    def lies(self):
        return self._raw.get('lies').get('totalLies')

    def resistance(self):
        return self._raw.get('resistance').get('extension',None)

    def summary_pretty(self):
        return f"Device: {self.device()}, Browser: {self.browser()}, Headless Rating: {self.headlessRating()}, Stealth Rating: {self.stealthRating()}, Timezone: {self.timezone()}, Lies: {self.lies()}, Resistance: {self.resistance()}"
    
    def summary(self):
        return {
            'digest': self.digest(),
            'stable_digest': self.stable_digest(),
            'is_bot': self.is_bot(),
            'bot_type': self.bot_type(),
            'device': self._raw['navigator']['device'],
            'browser': self._raw['navigator']['userAgentParsed'],
            'browserPrivateMode': self._raw['navigator'].get('doNotTrack', None),
            'headlessRating': self._raw['headless']['headlessRating'],
            'stealthRating': self._raw['headless']['stealthRating'],
            'timezone': self._raw['timezone']['zone'],
            'lies': self._raw['lies']['totalLies'],
            'resistance': self._raw['resistance'],
        }