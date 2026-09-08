from __future__ import annotations

# Imports Begin
from src.main.org.apache.commons.validator.routines.RegexValidator import *
import os
import typing
from typing import *
import io
import bisect

# Imports End


class ArrayType:

    # Class Fields Begin
    GENERIC_PLUS: ArrayType = None
    GENERIC_MINUS: ArrayType = None
    COUNTRY_CODE_PLUS: ArrayType = None
    COUNTRY_CODE_MINUS: ArrayType = None
    GENERIC_RO: ArrayType = None
    COUNTRY_CODE_RO: ArrayType = None
    INFRASTRUCTURE_RO: ArrayType = None
    LOCAL_RO: ArrayType = None
    LOCAL_PLUS: ArrayType = None
    LOCAL_MINUS: ArrayType = None
    # Class Fields End

    # Class Methods Begin
    def __init__(self, name: str) -> None:
        self.__name = name

    def __repr__(self) -> str:
        return "ArrayType." + self.__name

    def __str__(self) -> str:
        return self.__name

    # Class Methods End


ArrayType.GENERIC_PLUS = ArrayType("GENERIC_PLUS")
ArrayType.GENERIC_MINUS = ArrayType("GENERIC_MINUS")
ArrayType.COUNTRY_CODE_PLUS = ArrayType("COUNTRY_CODE_PLUS")
ArrayType.COUNTRY_CODE_MINUS = ArrayType("COUNTRY_CODE_MINUS")
ArrayType.GENERIC_RO = ArrayType("GENERIC_RO")
ArrayType.COUNTRY_CODE_RO = ArrayType("COUNTRY_CODE_RO")
ArrayType.INFRASTRUCTURE_RO = ArrayType("INFRASTRUCTURE_RO")
ArrayType.LOCAL_RO = ArrayType("LOCAL_RO")
ArrayType.LOCAL_PLUS = ArrayType("LOCAL_PLUS")
ArrayType.LOCAL_MINUS = ArrayType("LOCAL_MINUS")


class IDNBUGHOLDER:

    # Class Fields Begin
    __IDN_TOASCII_PRESERVES_TRAILING_DOTS: bool = None
    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def __keepsTrailingDot() -> bool:
        input_ = "a."  # must be a valid name
        try:
            return input_ == input_.encode("idna").decode("ascii")
        except UnicodeError:
            return False

    # Class Methods End


IDNBUGHOLDER._IDNBUGHOLDER__IDN_TOASCII_PRESERVES_TRAILING_DOTS = (
    IDNBUGHOLDER._IDNBUGHOLDER__keepsTrailingDot()
)


class Item:

    # Class Fields Begin
    type: ArrayType = None
    values: typing.List[typing.List[str]] = None
    # Class Fields End

    # Class Methods Begin
    def __init__(self, type_: ArrayType, values: typing.List[typing.List[str]]) -> None:
        self.type = type_
        self.values = values

    # Class Methods End


class LazyHolder:

    # Class Fields Begin
    __DOMAIN_VALIDATOR: DomainValidator = None
    __DOMAIN_VALIDATOR_WITH_LOCAL: DomainValidator = None
    # Class Fields End

    # Class Methods Begin
    # Class Methods End


class DomainValidator:

    # Class Fields Begin
    mycountryCodeTLDsMinus: typing.List[typing.List[str]] = None
    mycountryCodeTLDsPlus: typing.List[typing.List[str]] = None
    mygenericTLDsPlus: typing.List[typing.List[str]] = None
    mygenericTLDsMinus: typing.List[typing.List[str]] = None
    mylocalTLDsPlus: typing.List[typing.List[str]] = None
    mylocalTLDsMinus: typing.List[typing.List[str]] = None
    __inUse: bool = False
    __countryCodeTLDsPlus: typing.List[str] = []
    __genericTLDsPlus: typing.List[str] = []
    __countryCodeTLDsMinus: typing.List[str] = []
    __genericTLDsMinus: typing.List[str] = []
    __localTLDsMinus: typing.List[str] = []
    __localTLDsPlus: typing.List[str] = []
    __MAX_DOMAIN_LENGTH: int = 253
    __EMPTY_STRING_ARRAY: typing.List[str] = []
    __serialVersionUID: int = -4407125112880174009
    __DOMAIN_LABEL_REGEX: str = r"[A-Za-z0-9](?>[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    __TOP_LABEL_REGEX: str = r"[A-Za-z](?>[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    __DOMAIN_NAME_REGEX: str = None
    __UNEXPECTED_ENUM_VALUE: str = "Unexpected enum value: "
    __allowLocal: bool = None
    __domainRegex: RegexValidator = None
    __hostnameRegex: RegexValidator = None

    __INFRASTRUCTURE_TLDS: typing.List[str] = [
        'arpa',
    ]

    __GENERIC_TLDS: typing.List[str] = [
        'aaa',
        'aarp',
        'abarth',
        'abb',
        'abbott',
        'abbvie',
        'abc',
        'able',
        'abogado',
        'abudhabi',
        'academy',
        'accenture',
        'accountant',
        'accountants',
        'aco',
        'actor',
        'adac',
        'ads',
        'adult',
        'aeg',
        'aero',
        'aetna',
        'afamilycompany',
        'afl',
        'africa',
        'agakhan',
        'agency',
        'aig',
        'airbus',
        'airforce',
        'airtel',
        'akdn',
        'alfaromeo',
        'alibaba',
        'alipay',
        'allfinanz',
        'allstate',
        'ally',
        'alsace',
        'alstom',
        'amazon',
        'americanexpress',
        'americanfamily',
        'amex',
        'amfam',
        'amica',
        'amsterdam',
        'analytics',
        'android',
        'anquan',
        'anz',
        'aol',
        'apartments',
        'app',
        'apple',
        'aquarelle',
        'arab',
        'aramco',
        'archi',
        'army',
        'art',
        'arte',
        'asda',
        'asia',
        'associates',
        'athleta',
        'attorney',
        'auction',
        'audi',
        'audible',
        'audio',
        'auspost',
        'author',
        'auto',
        'autos',
        'avianca',
        'aws',
        'axa',
        'azure',
        'baby',
        'baidu',
        'banamex',
        'bananarepublic',
        'band',
        'bank',
        'bar',
        'barcelona',
        'barclaycard',
        'barclays',
        'barefoot',
        'bargains',
        'baseball',
        'basketball',
        'bauhaus',
        'bayern',
        'bbc',
        'bbt',
        'bbva',
        'bcg',
        'bcn',
        'beats',
        'beauty',
        'beer',
        'bentley',
        'berlin',
        'best',
        'bestbuy',
        'bet',
        'bharti',
        'bible',
        'bid',
        'bike',
        'bing',
        'bingo',
        'bio',
        'biz',
        'black',
        'blackfriday',
        'blockbuster',
        'blog',
        'bloomberg',
        'blue',
        'bms',
        'bmw',
        'bnpparibas',
        'boats',
        'boehringer',
        'bofa',
        'bom',
        'bond',
        'boo',
        'book',
        'booking',
        'bosch',
        'bostik',
        'boston',
        'bot',
        'boutique',
        'box',
        'bradesco',
        'bridgestone',
        'broadway',
        'broker',
        'brother',
        'brussels',
        'budapest',
        'bugatti',
        'build',
        'builders',
        'business',
        'buy',
        'buzz',
        'bzh',
        'cab',
        'cafe',
        'cal',
        'call',
        'calvinklein',
        'cam',
        'camera',
        'camp',
        'cancerresearch',
        'canon',
        'capetown',
        'capital',
        'capitalone',
        'car',
        'caravan',
        'cards',
        'care',
        'career',
        'careers',
        'cars',
        'casa',
        'case',
        'caseih',
        'cash',
        'casino',
        'cat',
        'catering',
        'catholic',
        'cba',
        'cbn',
        'cbre',
        'cbs',
        'ceb',
        'center',
        'ceo',
        'cern',
        'cfa',
        'cfd',
        'chanel',
        'channel',
        'charity',
        'chase',
        'chat',
        'cheap',
        'chintai',
        'christmas',
        'chrome',
        'church',
        'cipriani',
        'circle',
        'cisco',
        'citadel',
        'citi',
        'citic',
        'city',
        'cityeats',
        'claims',
        'cleaning',
        'click',
        'clinic',
        'clinique',
        'clothing',
        'cloud',
        'club',
        'clubmed',
        'coach',
        'codes',
        'coffee',
        'college',
        'cologne',
        'com',
        'comcast',
        'commbank',
        'community',
        'company',
        'compare',
        'computer',
        'comsec',
        'condos',
        'construction',
        'consulting',
        'contact',
        'contractors',
        'cooking',
        'cookingchannel',
        'cool',
        'coop',
        'corsica',
        'country',
        'coupon',
        'coupons',
        'courses',
        'cpa',
        'credit',
        'creditcard',
        'creditunion',
        'cricket',
        'crown',
        'crs',
        'cruise',
        'cruises',
        'csc',
        'cuisinella',
        'cymru',
        'cyou',
        'dabur',
        'dad',
        'dance',
        'data',
        'date',
        'dating',
        'datsun',
        'day',
        'dclk',
        'dds',
        'deal',
        'dealer',
        'deals',
        'degree',
        'delivery',
        'dell',
        'deloitte',
        'delta',
        'democrat',
        'dental',
        'dentist',
        'desi',
        'design',
        'dev',
        'dhl',
        'diamonds',
        'diet',
        'digital',
        'direct',
        'directory',
        'discount',
        'discover',
        'dish',
        'diy',
        'dnp',
        'docs',
        'doctor',
        'dog',
        'domains',
        'dot',
        'download',
        'drive',
        'dtv',
        'dubai',
        'duck',
        'dunlop',
        'dupont',
        'durban',
        'dvag',
        'dvr',
        'earth',
        'eat',
        'eco',
        'edeka',
        'edu',
        'education',
        'email',
        'emerck',
        'energy',
        'engineer',
        'engineering',
        'enterprises',
        'epson',
        'equipment',
        'ericsson',
        'erni',
        'esq',
        'estate',
        'etisalat',
        'eurovision',
        'eus',
        'events',
        'exchange',
        'expert',
        'exposed',
        'express',
        'extraspace',
        'fage',
        'fail',
        'fairwinds',
        'faith',
        'family',
        'fan',
        'fans',
        'farm',
        'farmers',
        'fashion',
        'fast',
        'fedex',
        'feedback',
        'ferrari',
        'ferrero',
        'fiat',
        'fidelity',
        'fido',
        'film',
        'final',
        'finance',
        'financial',
        'fire',
        'firestone',
        'firmdale',
        'fish',
        'fishing',
        'fit',
        'fitness',
        'flickr',
        'flights',
        'flir',
        'florist',
        'flowers',
        'fly',
        'foo',
        'food',
        'foodnetwork',
        'football',
        'ford',
        'forex',
        'forsale',
        'forum',
        'foundation',
        'fox',
        'free',
        'fresenius',
        'frl',
        'frogans',
        'frontdoor',
        'frontier',
        'ftr',
        'fujitsu',
        'fujixerox',
        'fun',
        'fund',
        'furniture',
        'futbol',
        'fyi',
        'gal',
        'gallery',
        'gallo',
        'gallup',
        'game',
        'games',
        'gap',
        'garden',
        'gay',
        'gbiz',
        'gdn',
        'gea',
        'gent',
        'genting',
        'george',
        'ggee',
        'gift',
        'gifts',
        'gives',
        'giving',
        'glade',
        'glass',
        'gle',
        'global',
        'globo',
        'gmail',
        'gmbh',
        'gmo',
        'gmx',
        'godaddy',
        'gold',
        'goldpoint',
        'golf',
        'goo',
        'goodyear',
        'goog',
        'google',
        'gop',
        'got',
        'gov',
        'grainger',
        'graphics',
        'gratis',
        'green',
        'gripe',
        'grocery',
        'group',
        'guardian',
        'gucci',
        'guge',
        'guide',
        'guitars',
        'guru',
        'hair',
        'hamburg',
        'hangout',
        'haus',
        'hbo',
        'hdfc',
        'hdfcbank',
        'health',
        'healthcare',
        'help',
        'helsinki',
        'here',
        'hermes',
        'hgtv',
        'hiphop',
        'hisamitsu',
        'hitachi',
        'hiv',
        'hkt',
        'hockey',
        'holdings',
        'holiday',
        'homedepot',
        'homegoods',
        'homes',
        'homesense',
        'honda',
        'horse',
        'hospital',
        'host',
        'hosting',
        'hot',
        'hoteles',
        'hotels',
        'hotmail',
        'house',
        'how',
        'hsbc',
        'hughes',
        'hyatt',
        'hyundai',
        'ibm',
        'icbc',
        'ice',
        'icu',
        'ieee',
        'ifm',
        'ikano',
        'imamat',
        'imdb',
        'immo',
        'immobilien',
        'inc',
        'industries',
        'infiniti',
        'info',
        'ing',
        'ink',
        'institute',
        'insurance',
        'insure',
        'int',
        'intel',
        'international',
        'intuit',
        'investments',
        'ipiranga',
        'irish',
        'ismaili',
        'ist',
        'istanbul',
        'itau',
        'itv',
        'iveco',
        'jaguar',
        'java',
        'jcb',
        'jcp',
        'jeep',
        'jetzt',
        'jewelry',
        'jio',
        'jll',
        'jmp',
        'jnj',
        'jobs',
        'joburg',
        'jot',
        'joy',
        'jpmorgan',
        'jprs',
        'juegos',
        'juniper',
        'kaufen',
        'kddi',
        'kerryhotels',
        'kerrylogistics',
        'kerryproperties',
        'kfh',
        'kia',
        'kim',
        'kinder',
        'kindle',
        'kitchen',
        'kiwi',
        'koeln',
        'komatsu',
        'kosher',
        'kpmg',
        'kpn',
        'krd',
        'kred',
        'kuokgroup',
        'kyoto',
        'lacaixa',
        'lamborghini',
        'lamer',
        'lancaster',
        'lancia',
        'land',
        'landrover',
        'lanxess',
        'lasalle',
        'lat',
        'latino',
        'latrobe',
        'law',
        'lawyer',
        'lds',
        'lease',
        'leclerc',
        'lefrak',
        'legal',
        'lego',
        'lexus',
        'lgbt',
        'lidl',
        'life',
        'lifeinsurance',
        'lifestyle',
        'lighting',
        'like',
        'lilly',
        'limited',
        'limo',
        'lincoln',
        'linde',
        'link',
        'lipsy',
        'live',
        'living',
        'lixil',
        'llc',
        'llp',
        'loan',
        'loans',
        'locker',
        'locus',
        'loft',
        'lol',
        'london',
        'lotte',
        'lotto',
        'love',
        'lpl',
        'lplfinancial',
        'ltd',
        'ltda',
        'lundbeck',
        'lupin',
        'luxe',
        'luxury',
        'macys',
        'madrid',
        'maif',
        'maison',
        'makeup',
        'man',
        'management',
        'mango',
        'map',
        'market',
        'marketing',
        'markets',
        'marriott',
        'marshalls',
        'maserati',
        'mattel',
        'mba',
        'mckinsey',
        'med',
        'media',
        'meet',
        'melbourne',
        'meme',
        'memorial',
        'men',
        'menu',
        'merckmsd',
        'metlife',
        'miami',
        'microsoft',
        'mil',
        'mini',
        'mint',
        'mit',
        'mitsubishi',
        'mlb',
        'mls',
        'mma',
        'mobi',
        'mobile',
        'moda',
        'moe',
        'moi',
        'mom',
        'monash',
        'money',
        'monster',
        'mormon',
        'mortgage',
        'moscow',
        'moto',
        'motorcycles',
        'mov',
        'movie',
        'msd',
        'mtn',
        'mtr',
        'museum',
        'mutual',
        'nab',
        'nagoya',
        'name',
        'nationwide',
        'natura',
        'navy',
        'nba',
        'nec',
        'net',
        'netbank',
        'netflix',
        'network',
        'neustar',
        'new',
        'newholland',
        'news',
        'next',
        'nextdirect',
        'nexus',
        'nfl',
        'ngo',
        'nhk',
        'nico',
        'nike',
        'nikon',
        'ninja',
        'nissan',
        'nissay',
        'nokia',
        'northwesternmutual',
        'norton',
        'now',
        'nowruz',
        'nowtv',
        'nra',
        'nrw',
        'ntt',
        'nyc',
        'obi',
        'observer',
        'off',
        'office',
        'okinawa',
        'olayan',
        'olayangroup',
        'oldnavy',
        'ollo',
        'omega',
        'one',
        'ong',
        'onl',
        'online',
        'onyourside',
        'ooo',
        'open',
        'oracle',
        'orange',
        'org',
        'organic',
        'origins',
        'osaka',
        'otsuka',
        'ott',
        'ovh',
        'page',
        'panasonic',
        'paris',
        'pars',
        'partners',
        'parts',
        'party',
        'passagens',
        'pay',
        'pccw',
        'pet',
        'pfizer',
        'pharmacy',
        'phd',
        'philips',
        'phone',
        'photo',
        'photography',
        'photos',
        'physio',
        'pics',
        'pictet',
        'pictures',
        'pid',
        'pin',
        'ping',
        'pink',
        'pioneer',
        'pizza',
        'place',
        'play',
        'playstation',
        'plumbing',
        'plus',
        'pnc',
        'pohl',
        'poker',
        'politie',
        'porn',
        'post',
        'pramerica',
        'praxi',
        'press',
        'prime',
        'pro',
        'prod',
        'productions',
        'prof',
        'progressive',
        'promo',
        'properties',
        'property',
        'protection',
        'pru',
        'prudential',
        'pub',
        'pwc',
        'qpon',
        'quebec',
        'quest',
        'qvc',
        'racing',
        'radio',
        'raid',
        'read',
        'realestate',
        'realtor',
        'realty',
        'recipes',
        'red',
        'redstone',
        'redumbrella',
        'rehab',
        'reise',
        'reisen',
        'reit',
        'reliance',
        'ren',
        'rent',
        'rentals',
        'repair',
        'report',
        'republican',
        'rest',
        'restaurant',
        'review',
        'reviews',
        'rexroth',
        'rich',
        'richardli',
        'ricoh',
        'ril',
        'rio',
        'rip',
        'rmit',
        'rocher',
        'rocks',
        'rodeo',
        'rogers',
        'room',
        'rsvp',
        'rugby',
        'ruhr',
        'run',
        'rwe',
        'ryukyu',
        'saarland',
        'safe',
        'safety',
        'sakura',
        'sale',
        'salon',
        'samsclub',
        'samsung',
        'sandvik',
        'sandvikcoromant',
        'sanofi',
        'sap',
        'sarl',
        'sas',
        'save',
        'saxo',
        'sbi',
        'sbs',
        'sca',
        'scb',
        'schaeffler',
        'schmidt',
        'scholarships',
        'school',
        'schule',
        'schwarz',
        'science',
        'scjohnson',
        'scot',
        'search',
        'seat',
        'secure',
        'security',
        'seek',
        'select',
        'sener',
        'services',
        'ses',
        'seven',
        'sew',
        'sex',
        'sexy',
        'sfr',
        'shangrila',
        'sharp',
        'shaw',
        'shell',
        'shia',
        'shiksha',
        'shoes',
        'shop',
        'shopping',
        'shouji',
        'show',
        'showtime',
        'shriram',
        'silk',
        'sina',
        'singles',
        'site',
        'ski',
        'skin',
        'sky',
        'skype',
        'sling',
        'smart',
        'smile',
        'sncf',
        'soccer',
        'social',
        'softbank',
        'software',
        'sohu',
        'solar',
        'solutions',
        'song',
        'sony',
        'soy',
        'space',
        'sport',
        'spot',
        'spreadbetting',
        'srl',
        'stada',
        'staples',
        'star',
        'statebank',
        'statefarm',
        'stc',
        'stcgroup',
        'stockholm',
        'storage',
        'store',
        'stream',
        'studio',
        'study',
        'style',
        'sucks',
        'supplies',
        'supply',
        'support',
        'surf',
        'surgery',
        'suzuki',
        'swatch',
        'swiftcover',
        'swiss',
        'sydney',
        'systems',
        'tab',
        'taipei',
        'talk',
        'taobao',
        'target',
        'tatamotors',
        'tatar',
        'tattoo',
        'tax',
        'taxi',
        'tci',
        'tdk',
        'team',
        'tech',
        'technology',
        'tel',
        'temasek',
        'tennis',
        'teva',
        'thd',
        'theater',
        'theatre',
        'tiaa',
        'tickets',
        'tienda',
        'tiffany',
        'tips',
        'tires',
        'tirol',
        'tjmaxx',
        'tjx',
        'tkmaxx',
        'tmall',
        'today',
        'tokyo',
        'tools',
        'top',
        'toray',
        'toshiba',
        'total',
        'tours',
        'town',
        'toyota',
        'toys',
        'trade',
        'trading',
        'training',
        'travel',
        'travelchannel',
        'travelers',
        'travelersinsurance',
        'trust',
        'trv',
        'tube',
        'tui',
        'tunes',
        'tushu',
        'tvs',
        'ubank',
        'ubs',
        'unicom',
        'university',
        'uno',
        'uol',
        'ups',
        'vacations',
        'vana',
        'vanguard',
        'vegas',
        'ventures',
        'verisign',
        'versicherung',
        'vet',
        'viajes',
        'video',
        'vig',
        'viking',
        'villas',
        'vin',
        'vip',
        'virgin',
        'visa',
        'vision',
        'viva',
        'vivo',
        'vlaanderen',
        'vodka',
        'volkswagen',
        'volvo',
        'vote',
        'voting',
        'voto',
        'voyage',
        'vuelos',
        'wales',
        'walmart',
        'walter',
        'wang',
        'wanggou',
        'watch',
        'watches',
        'weather',
        'weatherchannel',
        'webcam',
        'weber',
        'website',
        'wed',
        'wedding',
        'weibo',
        'weir',
        'whoswho',
        'wien',
        'wiki',
        'williamhill',
        'win',
        'windows',
        'wine',
        'winners',
        'wme',
        'wolterskluwer',
        'woodside',
        'work',
        'works',
        'world',
        'wow',
        'wtc',
        'wtf',
        'xbox',
        'xerox',
        'xfinity',
        'xihuan',
        'xin',
        'xn--11b4c3d',
        'xn--1ck2e1b',
        'xn--1qqw23a',
        'xn--30rr7y',
        'xn--3bst00m',
        'xn--3ds443g',
        'xn--3oq18vl8pn36a',
        'xn--3pxu8k',
        'xn--42c2d9a',
        'xn--45q11c',
        'xn--4gbrim',
        'xn--55qw42g',
        'xn--55qx5d',
        'xn--5su34j936bgsg',
        'xn--5tzm5g',
        'xn--6frz82g',
        'xn--6qq986b3xl',
        'xn--80adxhks',
        'xn--80aqecdr1a',
        'xn--80asehdb',
        'xn--80aswg',
        'xn--8y0a063a',
        'xn--90ae',
        'xn--9dbq2a',
        'xn--9et52u',
        'xn--9krt00a',
        'xn--b4w605ferd',
        'xn--bck1b9a5dre4c',
        'xn--c1avg',
        'xn--c2br7g',
        'xn--cck2b3b',
        'xn--cckwcxetd',
        'xn--cg4bki',
        'xn--czr694b',
        'xn--czrs0t',
        'xn--czru2d',
        'xn--d1acj3b',
        'xn--eckvdtc9d',
        'xn--efvy88h',
        'xn--fct429k',
        'xn--fhbei',
        'xn--fiq228c5hs',
        'xn--fiq64b',
        'xn--fjq720a',
        'xn--flw351e',
        'xn--fzys8d69uvgm',
        'xn--g2xx48c',
        'xn--gckr3f0f',
        'xn--gk3at1e',
        'xn--hxt814e',
        'xn--i1b6b1a6a2e',
        'xn--imr513n',
        'xn--io0a7i',
        'xn--j1aef',
        'xn--jlq480n2rg',
        'xn--jlq61u9w7b',
        'xn--jvr189m',
        'xn--kcrx77d1x4a',
        'xn--kput3i',
        'xn--mgba3a3ejt',
        'xn--mgba7c0bbn0a',
        'xn--mgbaakc7dvf',
        'xn--mgbab2bd',
        'xn--mgbca7dzdo',
        'xn--mgbi4ecexp',
        'xn--mgbt3dhd',
        'xn--mk1bu44c',
        'xn--mxtq1m',
        'xn--ngbc5azd',
        'xn--ngbe9e0a',
        'xn--ngbrx',
        'xn--nqv7f',
        'xn--nqv7fs00ema',
        'xn--nyqy26a',
        'xn--otu796d',
        'xn--p1acf',
        'xn--pssy2u',
        'xn--q9jyb4c',
        'xn--qcka1pmc',
        'xn--rhqv96g',
        'xn--rovu88b',
        'xn--ses554g',
        'xn--t60b56a',
        'xn--tckwe',
        'xn--tiq49xqyj',
        'xn--unup4y',
        'xn--vermgensberater-ctb',
        'xn--vermgensberatung-pwb',
        'xn--vhquv',
        'xn--vuq861b',
        'xn--w4r85el8fhu5dnra',
        'xn--w4rs40l',
        'xn--xhq521b',
        'xn--zfr164b',
        'xxx',
        'xyz',
        'yachts',
        'yahoo',
        'yamaxun',
        'yandex',
        'yodobashi',
        'yoga',
        'yokohama',
        'you',
        'youtube',
        'yun',
        'zappos',
        'zara',
        'zero',
        'zip',
        'zone',
        'zuerich',
    ]

    __COUNTRY_CODE_TLDS: typing.List[str] = [
        'ac',
        'ad',
        'ae',
        'af',
        'ag',
        'ai',
        'al',
        'am',
        'ao',
        'aq',
        'ar',
        'as',
        'at',
        'au',
        'aw',
        'ax',
        'az',
        'ba',
        'bb',
        'bd',
        'be',
        'bf',
        'bg',
        'bh',
        'bi',
        'bj',
        'bm',
        'bn',
        'bo',
        'br',
        'bs',
        'bt',
        'bv',
        'bw',
        'by',
        'bz',
        'ca',
        'cc',
        'cd',
        'cf',
        'cg',
        'ch',
        'ci',
        'ck',
        'cl',
        'cm',
        'cn',
        'co',
        'cr',
        'cu',
        'cv',
        'cw',
        'cx',
        'cy',
        'cz',
        'de',
        'dj',
        'dk',
        'dm',
        'do',
        'dz',
        'ec',
        'ee',
        'eg',
        'er',
        'es',
        'et',
        'eu',
        'fi',
        'fj',
        'fk',
        'fm',
        'fo',
        'fr',
        'ga',
        'gb',
        'gd',
        'ge',
        'gf',
        'gg',
        'gh',
        'gi',
        'gl',
        'gm',
        'gn',
        'gp',
        'gq',
        'gr',
        'gs',
        'gt',
        'gu',
        'gw',
        'gy',
        'hk',
        'hm',
        'hn',
        'hr',
        'ht',
        'hu',
        'id',
        'ie',
        'il',
        'im',
        'in',
        'io',
        'iq',
        'ir',
        'is',
        'it',
        'je',
        'jm',
        'jo',
        'jp',
        'ke',
        'kg',
        'kh',
        'ki',
        'km',
        'kn',
        'kp',
        'kr',
        'kw',
        'ky',
        'kz',
        'la',
        'lb',
        'lc',
        'li',
        'lk',
        'lr',
        'ls',
        'lt',
        'lu',
        'lv',
        'ly',
        'ma',
        'mc',
        'md',
        'me',
        'mg',
        'mh',
        'mk',
        'ml',
        'mm',
        'mn',
        'mo',
        'mp',
        'mq',
        'mr',
        'ms',
        'mt',
        'mu',
        'mv',
        'mw',
        'mx',
        'my',
        'mz',
        'na',
        'nc',
        'ne',
        'nf',
        'ng',
        'ni',
        'nl',
        'no',
        'np',
        'nr',
        'nu',
        'nz',
        'om',
        'pa',
        'pe',
        'pf',
        'pg',
        'ph',
        'pk',
        'pl',
        'pm',
        'pn',
        'pr',
        'ps',
        'pt',
        'pw',
        'py',
        'qa',
        're',
        'ro',
        'rs',
        'ru',
        'rw',
        'sa',
        'sb',
        'sc',
        'sd',
        'se',
        'sg',
        'sh',
        'si',
        'sj',
        'sk',
        'sl',
        'sm',
        'sn',
        'so',
        'sr',
        'ss',
        'st',
        'su',
        'sv',
        'sx',
        'sy',
        'sz',
        'tc',
        'td',
        'tf',
        'tg',
        'th',
        'tj',
        'tk',
        'tl',
        'tm',
        'tn',
        'to',
        'tr',
        'tt',
        'tv',
        'tw',
        'tz',
        'ua',
        'ug',
        'uk',
        'us',
        'uy',
        'uz',
        'va',
        'vc',
        've',
        'vg',
        'vi',
        'vn',
        'vu',
        'wf',
        'ws',
        'xn--2scrj9c',
        'xn--3e0b707e',
        'xn--3hcrj9c',
        'xn--45br5cyl',
        'xn--45brj9c',
        'xn--54b7fta0cc',
        'xn--80ao21a',
        'xn--90a3ac',
        'xn--90ais',
        'xn--clchc0ea0b2g2a9gcd',
        'xn--d1alf',
        'xn--e1a4c',
        'xn--fiqs8s',
        'xn--fiqz9s',
        'xn--fpcrj9c3d',
        'xn--fzc2c9e2c',
        'xn--gecrj9c',
        'xn--h2breg3eve',
        'xn--h2brj9c',
        'xn--h2brj9c8c',
        'xn--j1amh',
        'xn--j6w193g',
        'xn--kprw13d',
        'xn--kpry57d',
        'xn--l1acc',
        'xn--lgbbat1ad8j',
        'xn--mgb9awbf',
        'xn--mgba3a4f16a',
        'xn--mgbaam7a8h',
        'xn--mgbah1a3hjkrd',
        'xn--mgbai9azgqp6j',
        'xn--mgbayh7gpa',
        'xn--mgbbh1a',
        'xn--mgbbh1a71e',
        'xn--mgbc0a9azcg',
        'xn--mgbcpq6gpa1a',
        'xn--mgberp4a5d4ar',
        'xn--mgbgu82a',
        'xn--mgbpl2fh',
        'xn--mgbtx2b',
        'xn--mgbx4cd0ab',
        'xn--mix891f',
        'xn--node',
        'xn--o3cw4h',
        'xn--ogbpf8fl',
        'xn--p1ai',
        'xn--pgbs0dh',
        'xn--q7ce6a',
        'xn--qxa6a',
        'xn--qxam',
        'xn--rvc1e0am3e',
        'xn--s9brj9c',
        'xn--wgbh1c',
        'xn--wgbl6a',
        'xn--xkc2al3hye2a',
        'xn--xkc2dl3a5ee0h',
        'xn--y9a3aq',
        'xn--yfro4i67o',
        'xn--ygbi2ammx',
        'ye',
        'yt',
        'za',
        'zm',
        'zw',
    ]

    __LOCAL_TLDS: typing.List[str] = [
        'localdomain',
        'localhost',
    ]

    # Class Fields End

    # Class Methods Begin
    @staticmethod
    def unicodeToASCII(input_: str) -> str:
        if DomainValidator._DomainValidator__isOnlyASCII(input_):
            return input_
        # java.net.IDN.toASCII treats U+002E, U+3002, U+FF0E and U+FF61 as
        # equivalent label separators (RFC 3490). Python's "idna" codec
        # already treats these as separators when they sit between real
        # labels, but it raises UnicodeError when the string is made up
        # of nothing but separator characters (e.g. a lone "\u3002"),
        # because that yields an empty label. Java's implementation is
        # lenient in that case and simply passes the (normalized)
        # separators through unchanged, so that edge case is special
        # cased here before delegating to the codec.
        normalized = input_
        for sep in ("\u3002", "\uFF0E", "\uFF61"):
            normalized = normalized.replace(sep, ".")
        if normalized != "" and normalized.strip(".") == "":
            return normalized
        try:
            ascii_ = input_.encode("idna").decode("ascii")
        except UnicodeError:
            return input_
        if IDNBUGHOLDER._IDNBUGHOLDER__IDN_TOASCII_PRESERVES_TRAILING_DOTS:
            return ascii_
        length = len(input_)
        if length == 0:
            return input_
        lastChar = input_[length - 1]
        if lastChar in ("\u002E", "\u3002", "\uFF0E", "\uFF61"):
            return ascii_ + "."
        return ascii_

    def getOverrides(self, table: ArrayType) -> typing.List[typing.List[str]]:
        if table is ArrayType.COUNTRY_CODE_MINUS:
            array = self.mycountryCodeTLDsMinus
        elif table is ArrayType.COUNTRY_CODE_PLUS:
            array = self.mycountryCodeTLDsPlus
        elif table is ArrayType.GENERIC_MINUS:
            array = self.mygenericTLDsMinus
        elif table is ArrayType.GENERIC_PLUS:
            array = self.mygenericTLDsPlus
        elif table is ArrayType.LOCAL_MINUS:
            array = self.mylocalTLDsMinus
        elif table is ArrayType.LOCAL_PLUS:
            array = self.mylocalTLDsPlus
        else:
            raise ValueError(DomainValidator.__UNEXPECTED_ENUM_VALUE + str(table))
        return list(array)

    @staticmethod
    def getTLDEntries(table: ArrayType) -> typing.List[typing.List[str]]:
        if table is ArrayType.COUNTRY_CODE_MINUS:
            array = DomainValidator.__countryCodeTLDsMinus
        elif table is ArrayType.COUNTRY_CODE_PLUS:
            array = DomainValidator.__countryCodeTLDsPlus
        elif table is ArrayType.GENERIC_MINUS:
            array = DomainValidator.__genericTLDsMinus
        elif table is ArrayType.GENERIC_PLUS:
            array = DomainValidator.__genericTLDsPlus
        elif table is ArrayType.LOCAL_MINUS:
            array = DomainValidator.__localTLDsMinus
        elif table is ArrayType.LOCAL_PLUS:
            array = DomainValidator.__localTLDsPlus
        elif table is ArrayType.GENERIC_RO:
            array = DomainValidator.__GENERIC_TLDS
        elif table is ArrayType.COUNTRY_CODE_RO:
            array = DomainValidator.__COUNTRY_CODE_TLDS
        elif table is ArrayType.INFRASTRUCTURE_RO:
            array = DomainValidator.__INFRASTRUCTURE_TLDS
        elif table is ArrayType.LOCAL_RO:
            array = DomainValidator.__LOCAL_TLDS
        else:
            raise ValueError(DomainValidator.__UNEXPECTED_ENUM_VALUE + str(table))
        return list(array)

    @staticmethod
    def updateTLDOverride(
        table: ArrayType, tlds: typing.List[typing.List[str]]
    ) -> None:
        if DomainValidator.__inUse:
            raise RuntimeError("Can only invoke this method before calling getInstance")
        copy = sorted(tld.lower() for tld in tlds)
        if table is ArrayType.COUNTRY_CODE_MINUS:
            DomainValidator.__countryCodeTLDsMinus = copy
        elif table is ArrayType.COUNTRY_CODE_PLUS:
            DomainValidator.__countryCodeTLDsPlus = copy
        elif table is ArrayType.GENERIC_MINUS:
            DomainValidator.__genericTLDsMinus = copy
        elif table is ArrayType.GENERIC_PLUS:
            DomainValidator.__genericTLDsPlus = copy
        elif table is ArrayType.LOCAL_MINUS:
            DomainValidator.__localTLDsMinus = copy
        elif table is ArrayType.LOCAL_PLUS:
            DomainValidator.__localTLDsPlus = copy
        elif table in (
            ArrayType.COUNTRY_CODE_RO,
            ArrayType.GENERIC_RO,
            ArrayType.INFRASTRUCTURE_RO,
            ArrayType.LOCAL_RO,
        ):
            raise ValueError("Cannot update the table: " + str(table))
        else:
            raise ValueError(DomainValidator.__UNEXPECTED_ENUM_VALUE + str(table))

    def isAllowLocal(self) -> bool:
        return self.__allowLocal

    def isValidLocalTld(self, lTld: str) -> bool:
        key = self.__chompLeadingDot(
            DomainValidator.unicodeToASCII(lTld).lower()
        )
        return (
            DomainValidator._DomainValidator__arrayContains(
                DomainValidator.__LOCAL_TLDS, key
            )
            or DomainValidator._DomainValidator__arrayContains(
                self.mylocalTLDsPlus, key
            )
        ) and not DomainValidator._DomainValidator__arrayContains(
            self.mylocalTLDsMinus, key
        )

    def isValidCountryCodeTld(self, ccTld: str) -> bool:
        key = self.__chompLeadingDot(
            DomainValidator.unicodeToASCII(ccTld).lower()
        )
        return (
            DomainValidator._DomainValidator__arrayContains(
                DomainValidator.__COUNTRY_CODE_TLDS, key
            )
            or DomainValidator._DomainValidator__arrayContains(
                self.mycountryCodeTLDsPlus, key
            )
        ) and not DomainValidator._DomainValidator__arrayContains(
            self.mycountryCodeTLDsMinus, key
        )

    def isValidGenericTld(self, gTld: str) -> bool:
        key = self.__chompLeadingDot(
            DomainValidator.unicodeToASCII(gTld).lower()
        )
        return (
            DomainValidator._DomainValidator__arrayContains(
                DomainValidator.__GENERIC_TLDS, key
            )
            or DomainValidator._DomainValidator__arrayContains(
                self.mygenericTLDsPlus, key
            )
        ) and not DomainValidator._DomainValidator__arrayContains(
            self.mygenericTLDsMinus, key
        )

    def isValidInfrastructureTld(self, iTld: str) -> bool:
        key = self.__chompLeadingDot(
            DomainValidator.unicodeToASCII(iTld).lower()
        )
        return DomainValidator._DomainValidator__arrayContains(
            DomainValidator.__INFRASTRUCTURE_TLDS, key
        )

    def isValidTld(self, tld: str) -> bool:
        if self.__allowLocal and self.isValidLocalTld(tld):
            return True
        return (
            self.isValidInfrastructureTld(tld)
            or self.isValidGenericTld(tld)
            or self.isValidCountryCodeTld(tld)
        )

    def isValidDomainSyntax(self, domain: str) -> bool:
        if domain is None:
            return False
        domain = DomainValidator.unicodeToASCII(domain)
        if len(domain) > DomainValidator.__MAX_DOMAIN_LENGTH:
            return False
        groups = self.__domainRegex.match(domain)
        return (groups is not None and len(groups) > 0) or self.__hostnameRegex.isValid(
            domain
        )

    def isValid(self, domain: str) -> bool:
        if domain is None:
            return False
        domain = DomainValidator.unicodeToASCII(domain)
        if len(domain) > DomainValidator.__MAX_DOMAIN_LENGTH:
            return False
        groups = self.__domainRegex.match(domain)
        if groups is not None and len(groups) > 0:
            return self.isValidTld(groups[0])
        return self.__allowLocal and self.__hostnameRegex.isValid(domain)

    def __init__(
        self, constructorId: int, items: typing.List[Item], allowLocal: bool
    ) -> None:
        if constructorId == 0:
            self.__allowLocal = allowLocal

            ccMinus = DomainValidator.__countryCodeTLDsMinus
            ccPlus = DomainValidator.__countryCodeTLDsPlus
            genMinus = DomainValidator.__genericTLDsMinus
            genPlus = DomainValidator.__genericTLDsPlus
            localMinus = DomainValidator.__localTLDsMinus
            localPlus = DomainValidator.__localTLDsPlus

            for item in items or []:
                copy = sorted(v.lower() for v in item.values)
                if item.type is ArrayType.COUNTRY_CODE_MINUS:
                    ccMinus = copy
                elif item.type is ArrayType.COUNTRY_CODE_PLUS:
                    ccPlus = copy
                elif item.type is ArrayType.GENERIC_MINUS:
                    genMinus = copy
                elif item.type is ArrayType.GENERIC_PLUS:
                    genPlus = copy
                elif item.type is ArrayType.LOCAL_MINUS:
                    localMinus = copy
                elif item.type is ArrayType.LOCAL_PLUS:
                    localPlus = copy

            self.mycountryCodeTLDsMinus = ccMinus
            self.mycountryCodeTLDsPlus = ccPlus
            self.mygenericTLDsMinus = genMinus
            self.mygenericTLDsPlus = genPlus
            self.mylocalTLDsMinus = localMinus
            self.mylocalTLDsPlus = localPlus
        else:
            self.__allowLocal = allowLocal
            self.mycountryCodeTLDsMinus = DomainValidator.__countryCodeTLDsMinus
            self.mycountryCodeTLDsPlus = DomainValidator.__countryCodeTLDsPlus
            self.mygenericTLDsPlus = DomainValidator.__genericTLDsPlus
            self.mygenericTLDsMinus = DomainValidator.__genericTLDsMinus
            self.mylocalTLDsPlus = DomainValidator.__localTLDsPlus
            self.mylocalTLDsMinus = DomainValidator.__localTLDsMinus

        self.__domainRegex = RegexValidator.RegexValidator3(
            DomainValidator.__DOMAIN_NAME_REGEX
        )
        self.__hostnameRegex = RegexValidator.RegexValidator3(
            DomainValidator.__DOMAIN_LABEL_REGEX
        )

    @staticmethod
    def getInstance2(allowLocal: bool, items: typing.List[Item]) -> DomainValidator:
        DomainValidator.__inUse = True
        return DomainValidator(0, items, allowLocal)

    @staticmethod
    def getInstance1(allowLocal: bool) -> DomainValidator:
        DomainValidator.__inUse = True
        if allowLocal:
            if getattr(LazyHolder, "_LazyHolder__DOMAIN_VALIDATOR_WITH_LOCAL", None) is None:
                setattr(
                    LazyHolder,
                    "_LazyHolder__DOMAIN_VALIDATOR_WITH_LOCAL",
                    DomainValidator(1, None, True),
                )
            return getattr(LazyHolder, "_LazyHolder__DOMAIN_VALIDATOR_WITH_LOCAL")
        if getattr(LazyHolder, "_LazyHolder__DOMAIN_VALIDATOR", None) is None:
            setattr(
                LazyHolder,
                "_LazyHolder__DOMAIN_VALIDATOR",
                DomainValidator(1, None, False),
            )
        return getattr(LazyHolder, "_LazyHolder__DOMAIN_VALIDATOR")

    @staticmethod
    def getInstance0() -> DomainValidator:
        DomainValidator.__inUse = True
        if getattr(LazyHolder, "_LazyHolder__DOMAIN_VALIDATOR", None) is None:
            setattr(
                LazyHolder,
                "_LazyHolder__DOMAIN_VALIDATOR",
                DomainValidator(1, None, False),
            )
        return getattr(LazyHolder, "_LazyHolder__DOMAIN_VALIDATOR")

    @staticmethod
    def __arrayContains(sortedArray: typing.List[typing.List[str]], key: str) -> bool:
        i = bisect.bisect_left(sortedArray, key)
        return i < len(sortedArray) and sortedArray[i] == key

    @staticmethod
    def __isOnlyASCII(input_: str) -> bool:
        if input_ is None:
            return True
        for ch in input_:
            if ord(ch) > 0x7F:
                return False
        return True

    def __chompLeadingDot(self, str_: str) -> str:
        if str_.startswith("."):
            return str_[1:]
        return str_

    # Class Methods End


DomainValidator._DomainValidator__DOMAIN_NAME_REGEX = (
    "^(?:"
    + DomainValidator._DomainValidator__DOMAIN_LABEL_REGEX
    + r"\.)+"
    + "("
    + DomainValidator._DomainValidator__TOP_LABEL_REGEX
    + r")\.?$"
)
