import getOfflineAudioContext, { audioHTML } from './audio'
import getCanvas2d, { canvasHTML } from './canvas'
import getCSS, { cssHTML } from './css'
import getCSSMedia, { cssMediaHTML } from './cssmedia'
import getHTMLElementVersion, { htmlElementVersionHTML } from './document'
import getClientRects, { clientRectsHTML } from './domrect'
import getConsoleErrors, { consoleErrorsHTML } from './engine'
import { timer, getCapturedErrors, caniuse, errorsHTML, attempt } from './errors'
import getEngineFeatures, { featuresHTML, getFeaturesLie } from './features'
import getFonts, { fontsHTML } from './fonts'
import getHeadlessFeatures, { headlessFeaturesHTML } from './headless'
import getIntl, { intlHTML } from './intl'
import { getLies, PARENT_PHANTOM, liesHTML, PROTO_BENCHMARK } from './lies'
import getMaths, { mathsHTML } from './math'
import getMedia, { mediaHTML } from './media'
import getNavigator, { navigatorHTML } from './navigator'
import getPrediction, { getBlankIcons, predictionErrorPatch, renderPrediction } from './prediction'
import getResistance, { resistanceHTML } from './resistance'
import renderSamples, { getSamples, getRawFingerprint } from './samples'
import getScreen, { screenHTML } from './screen'
import getVoices, { voicesHTML } from './speech'
import { getStatus, getStorage, statusHTML } from './status'
import getSVG, { svgHTML } from './svg'
import getTimezone, { timezoneHTML } from './timezone'
import { getTrash, trashHTML } from './trash'
import { hashify, hashMini, getBotHash, getFuzzyHash, cipher } from './utils/crypto'
import { exile, getStackBytes, getTTFB, measure } from './utils/exile'
import { IS_BLINK, braveBrowser, getBraveMode, getBraveUnprotectedParameters, computeWindowsRelease, hashSlice, ENGINE_IDENTIFIER, getUserAgentRestored, attemptWindows11UserAgent, LowerEntropy, queueTask, Analysis } from './utils/helpers'
import { patch, html, getDiffs, modal, HTMLNote } from './utils/html'
import getCanvasWebgl, { webglHTML } from './webgl'
import getWebRTCData, { getWebRTCDevices, webrtcHTML } from './webrtc'
import getWindowFeatures, { windowFeaturesHTML } from './window'
import getBestWorkerScope, { Scope, spawnWorker, workerScopeHTML } from './worker'

import { getFingerprint } from './driver'


!async function() {
	'use strict';

	const scope = await spawnWorker()

	if (scope == Scope.WORKER) {
		return
	}

	await queueTask()
	const stackBytes = getStackBytes()
	const [, measuredTime, ttfb] = await Promise.all([
		exile(),
		measure(),
		getTTFB(),
	])
	console.clear()
	const measured = (outerWidth - innerWidth < 150) && (outerHeight - innerHeight < 150) ? measuredTime : 0

	const isBrave = IS_BLINK ? await braveBrowser() : false
	const braveMode = isBrave ? getBraveMode() : {}
	const braveFingerprintingBlocking = isBrave && (braveMode.standard || braveMode.strict)

	//const fingerprint = await getFingerprint(braveFingerprintingBlocking)

	// fingerprint and render
	const [
		{
			fingerprint: fp,
			styleSystemHash,
			styleHash,
			domRectHash,
			mimeTypesHash,
			canvas2dImageHash,
			canvas2dPaintHash,
			canvas2dTextHash,
			canvas2dEmojiHash,
			canvasWebglImageHash,
			canvasWebglParametersHash,
			deviceOfTimezoneHash,
			timeEnd,
		},
		sQuota,
	] = await Promise.all([
		getFingerprint(braveFingerprintingBlocking).catch((error) => console.error(error)) || {},
		getStorage(),
	])

	if (!fp) {
		throw new Error('Fingerprint failed!')
	}

	const tmSum = +(fp.canvas2d?.textMetricsSystemSum) || 0
	const glBc = Analysis.webglBrandCapabilities

	// 🐲 Dragon fire
	if ((({
		'01299ea5': 1688108400000,
		'a2217a02': 1688108400000,
		'632ecc1d': 1688108400000,
		'520916bb': 1684998000000,
	})[hashMini([stackBytes, tmSum])] || +new Date()) > +new Date()) {
		try {
			const meta = document.createElement('meta')
			meta.httpEquiv = 'refresh'
			meta.content = `1;${atob('YWJvdXQ6Ymxhbms=')}`
			document.head.appendChild(meta)
		} catch {}
		// eslint-disable-next-line @typescript-eslint/no-empty-function, @typescript-eslint/no-unused-vars
		await new Promise((_) => { })
	}

	console.log('%c✔ loose fingerprint passed', 'color:#4cca9f')

	console.groupCollapsed('Loose Fingerprint')
	console.log(fp)
	console.groupEnd()

	console.groupCollapsed('Loose Fingerprint JSON')
	console.log('diff check at https://www.diffchecker.com/diff\n\n', JSON.stringify(fp, null, '\t'))
	console.groupEnd()

	// Trusted Fingerprint
	const trashLen = fp.trash.trashBin.length
	const liesLen = !('totalLies' in fp.lies) ? 0 : fp.lies.totalLies
	const errorsLen = fp.capturedErrors.data.length

	const hardenEntropy = (workerScope, prop) => {
		return (
			!workerScope ? prop :
				(workerScope.localeEntropyIsTrusty && workerScope.localeIntlEntropyIsTrusty) ? prop :
					undefined
		)
	}

	const privacyResistFingerprinting = (
		fp.resistance && /^(tor browser|firefox)$/i.test(fp.resistance.privacy)
	)

	// harden gpu
	const hardenGPU = (canvasWebgl) => {
		const { gpu: { confidence, compressedGPU } } = canvasWebgl
		return (
			confidence == 'low' ? {} : {
				UNMASKED_RENDERER_WEBGL: compressedGPU,
				UNMASKED_VENDOR_WEBGL: canvasWebgl.parameters.UNMASKED_VENDOR_WEBGL,
			}
		)
	}

	const creep = {
		navigator: (
			!fp.navigator || fp.navigator.lied ? undefined : {
				bluetoothAvailability: fp.navigator.bluetoothAvailability,
				device: fp.navigator.device,
				deviceMemory: fp.navigator.deviceMemory,
				hardwareConcurrency: fp.navigator.hardwareConcurrency,
				maxTouchPoints: fp.navigator.maxTouchPoints,
				oscpu: fp.navigator.oscpu,
				platform: fp.navigator.platform,
				system: fp.navigator.system,
				userAgentData: {
					...(fp.navigator.userAgentData || {}),
					// loose
					brandsVersion: undefined,
					uaFullVersion: undefined,
				},
				vendor: fp.navigator.vendor,
			}
		),
		screen: (
			!fp.screen || fp.screen.lied || privacyResistFingerprinting || LowerEntropy.SCREEN ? undefined :
				hardenEntropy(
					fp.workerScope, {
						height: fp.screen.height,
						width: fp.screen.width,
						pixelDepth: fp.screen.pixelDepth,
						colorDepth: fp.screen.colorDepth,
						lied: fp.screen.lied,
					},
				)
		),
		workerScope: !fp.workerScope || fp.workerScope.lied ? undefined : {
			deviceMemory: (
				braveFingerprintingBlocking ? undefined : fp.workerScope.deviceMemory
			),
			hardwareConcurrency: (
				braveFingerprintingBlocking ? undefined : fp.workerScope.hardwareConcurrency
			),
			// system locale in blink
			language: !LowerEntropy.TIME_ZONE ? fp.workerScope.language : undefined,
			platform: fp.workerScope.platform,
			system: fp.workerScope.system,
			device: fp.workerScope.device,
			timezoneLocation: (
				!LowerEntropy.TIME_ZONE ?
					hardenEntropy(fp.workerScope, fp.workerScope.timezoneLocation) :
						undefined
			),
			webglRenderer: (
				(fp.workerScope.gpu.confidence != 'low') ? fp.workerScope.gpu.compressedGPU : undefined
			),
			webglVendor: (
				(fp.workerScope.gpu.confidence != 'low') ? fp.workerScope.webglVendor : undefined
			),
			userAgentData: {
				...fp.workerScope.userAgentData,
				// loose
				brandsVersion: undefined,
				uaFullVersion: undefined,
			},
		},
		media: fp.media,
		canvas2d: ((canvas2d) => {
			if (!canvas2d) {
				return
			}
			const { lied, liedTextMetrics } = canvas2d
			let data
			if (!lied) {
				const { dataURI, paintURI, textURI, emojiURI } = canvas2d
				data = {
					lied,
					...{ dataURI, paintURI, textURI, emojiURI },
				}
			}
			if (!liedTextMetrics) {
				const { textMetricsSystemSum, emojiSet } = canvas2d
				data = {
					...(data || {}),
					...{ textMetricsSystemSum, emojiSet },
				}
			}
			return data
		})(fp.canvas2d),
		canvasWebgl: (!fp.canvasWebgl || fp.canvasWebgl.lied || LowerEntropy.WEBGL) ? undefined : (
			braveFingerprintingBlocking ? {
				parameters: {
					...getBraveUnprotectedParameters(fp.canvasWebgl.parameters),
					...hardenGPU(fp.canvasWebgl),
				},
			} : {
				...((gl, canvas2d) => {
					if ((canvas2d && canvas2d.lied) || LowerEntropy.CANVAS) {
						// distrust images
						const { extensions, gpu, lied, parameterOrExtensionLie } = gl
						return {
							extensions,
							gpu,
							lied,
							parameterOrExtensionLie,
						}
					}
					return gl
				})(fp.canvasWebgl, fp.canvas2d),
				parameters: {
					...fp.canvasWebgl.parameters,
					...hardenGPU(fp.canvasWebgl),
				},
			}
		),
		cssMedia: !fp.cssMedia ? undefined : {
			reducedMotion: caniuse(() => fp.cssMedia.mediaCSS['prefers-reduced-motion']),
			colorScheme: (
				braveFingerprintingBlocking ? undefined :
				caniuse(() => fp.cssMedia.mediaCSS['prefers-color-scheme'])
			),
			monochrome: caniuse(() => fp.cssMedia.mediaCSS.monochrome),
			invertedColors: caniuse(() => fp.cssMedia.mediaCSS['inverted-colors']),
			forcedColors: caniuse(() => fp.cssMedia.mediaCSS['forced-colors']),
			anyHover: caniuse(() => fp.cssMedia.mediaCSS['any-hover']),
			hover: caniuse(() => fp.cssMedia.mediaCSS.hover),
			anyPointer: caniuse(() => fp.cssMedia.mediaCSS['any-pointer']),
			pointer: caniuse(() => fp.cssMedia.mediaCSS.pointer),
			colorGamut: caniuse(() => fp.cssMedia.mediaCSS['color-gamut']),
			screenQuery: (
				privacyResistFingerprinting || (LowerEntropy.SCREEN || LowerEntropy.IFRAME_SCREEN) ?
					undefined :
						hardenEntropy(fp.workerScope, caniuse(() => fp.cssMedia.screenQuery))
			),
		},
		css: !fp.css ? undefined : fp.css.system.fonts,
		timezone: !fp.timezone || fp.timezone.lied || LowerEntropy.TIME_ZONE ? undefined : {
			locationMeasured: hardenEntropy(fp.workerScope, fp.timezone.locationMeasured),
			lied: fp.timezone.lied,
		},
		offlineAudioContext: !fp.offlineAudioContext ? undefined : (
			fp.offlineAudioContext.lied || LowerEntropy.AUDIO ? undefined :
				fp.offlineAudioContext
		),
		fonts: !fp.fonts || fp.fonts.lied || LowerEntropy.FONTS ? undefined : fp.fonts.fontFaceLoadFonts,
		forceRenew: 1682918207897,
	}

	console.log('%c✔ stable fingerprint passed', 'color:#4cca9f')

	console.groupCollapsed('Stable Fingerprint')
	console.log(creep)
	console.groupEnd()

	console.groupCollapsed('Stable Fingerprint JSON')
	console.log('diff check at https://www.diffchecker.com/diff\n\n', JSON.stringify(creep, null, '\t'))
	console.groupEnd()

	const fuzzyFingerprint = await getFuzzyHash(fp)
	console.log('%c✔ fuzzy fingerprint passed', 'color:#4cca9f', fuzzyFingerprint)

	const { botHash, badBot } = getBotHash(fp, { getFeaturesLie, computeWindowsRelease })
	console.log('%c✔ bot fingerprint passed', 'color:#4cca9f', botHash, badBot)
	

	const [fpHash, creepHash] = await Promise.all([hashify(fp), hashify(creep)]).catch((error) => {
		console.error(error.message)
	}) || []

	

	// session
	const computeSession = ({ fingerprint, loading = false, computePreviousLoadRevision = false }) => {
		const data = {
			revisedKeysFromPreviousLoad: [],
			revisedKeys: [],
			initial: '',
			loads: 0,
		}
		try {
			const currentFingerprint = Object.keys(fingerprint).reduce((acc, key) => {
				if (!fingerprint[key]) {
					return acc
				}
				acc[key] = fingerprint[key].$hash
				return acc
			}, {})
			// @ts-ignore
			const loads = +(sessionStorage.getItem('loads'))
			// @ts-ignore
			const initialFingerprint = JSON.parse(sessionStorage.getItem('initialFingerprint'))
			// @ts-ignore
			const previousFingerprint = JSON.parse(sessionStorage.getItem('previousFingerprint'))
			if (initialFingerprint) {
				data.initial = hashMini(initialFingerprint)
				if (loading) {
					data.loads = 1+loads
					sessionStorage.setItem('loads', ''+data.loads)
				} else {
					data.loads = loads
				}

				if (computePreviousLoadRevision) {
					sessionStorage.setItem('previousFingerprint', JSON.stringify(currentFingerprint))
				}

				const currentFingerprintKeys = Object.keys(currentFingerprint)
				const revisedKeysFromPreviousLoad = currentFingerprintKeys
					.filter((key) => currentFingerprint[key] != previousFingerprint[key])

				const revisedKeys = currentFingerprintKeys
					.filter((key) => currentFingerprint[key] != initialFingerprint[key])

				// @ts-ignore
				data.revisedKeys = revisedKeys.length ? revisedKeys : []
				// @ts-ignore
				data.revisedKeysFromPreviousLoad = revisedKeysFromPreviousLoad.length ? revisedKeysFromPreviousLoad : []
				return data
			}
			sessionStorage.setItem('initialFingerprint', JSON.stringify(currentFingerprint))
			sessionStorage.setItem('previousFingerprint', JSON.stringify(currentFingerprint))
			sessionStorage.setItem('loads', ''+1)
			data.initial = hashMini(currentFingerprint)
			data.loads = 1
			return data
		} catch (error) {
			console.error(error)
			return data
		}
	}

}()

