const SHOP_DATA = [];
const GACHA_DATA = [
    {
        "id": "1496901435684556970",
        "name": "一般人です",
        "type": "normal",
        "series": "通常",
        "stock": -1
    },
    {
        "id": "1497204772615491634",
        "name": "なでて",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497204858204323980",
        "name": "だいすき",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497204858204323980",
        "name": "だいすき",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497204858204323980",
        "name": "だいすき",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497204970481520701",
        "name": "構われ待ち",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497205075603623976",
        "name": "独占して",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497204970481520701",
        "name": "構われ待ち",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497205158692782172",
        "name": "養分",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497205320945111180",
        "name": "カモ",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497205425274224821",
        "name": "搾取対象",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497205518870249512",
        "name": "沼ってる人",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497205518870249512",
        "name": "沼ってる人",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497205518870249512",
        "name": "沼ってる人",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497205585437790278",
        "name": "金欠",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497205668619358380",
        "name": "限界オタク",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497206030315290816",
        "name": "口だけ最強",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497206404543414322",
        "name": "普通すぎる",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497206499506786436",
        "name": "印象薄い",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497206404543414322",
        "name": "普通すぎる",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497206816042647673",
        "name": "強者",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497206908006957066",
        "name": "上位勢",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497207010721136691",
        "name": "人外",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497207081315602503",
        "name": "ガチ勢",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497207151016542349",
        "name": "主人公補正",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497207225255727224",
        "name": "成金",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497207412937982052",
        "name": "札束ビンタ",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497207507528192031",
        "name": "無駄遣い王",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497207592370442300",
        "name": "石油王候補",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    },
    {
        "id": "1497207677753888778",
        "name": "例外存在",
        "type": "normal",
        "series": "ノーマル",
        "stock": -1
    }
];
const CURRENCY_NAME = '星';
const USER_PROFILES = {
    "tenya": {
        "name": "てんや",
        "avatar": "https://cdn.discordapp.com/avatars/1368428956214100062/29a23ac792889cfd274120aa8a823144.png?size=1024",
        "money": 68078,
        "subs_count": 19
    },
    "age0309": {
        "name": "m!dc",
        "avatar": "https://cdn.discordapp.com/guilds/1496790362294063114/users/1387724679225278484/avatars/b6bf077b975eea218fc289855c978d91.png?size=1024",
        "money": 9800,
        "subs_count": 5
    },
    "Sw0623": {
        "name": "愛＄",
        "avatar": "https://cdn.discordapp.com/avatars/1493287369322004643/9cc06637cc0bc75b238c6faf16dfb03e.png?size=1024",
        "money": 20000,
        "subs_count": 0
    },
    "lirve192": {
        "name": "m!p",
        "avatar": "https://cdn.discordapp.com/avatars/1393702468600336586/2811ac501f022fdaf7c7e4c72d2107bb.png?size=1024",
        "money": 0,
        "subs_count": 2
    }
};