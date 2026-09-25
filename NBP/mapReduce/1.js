db.cards.mapReduce(
  function () {
    if (this.text) {
       this.text.split(/\s+/).forEach(function (word) {
         var cleanWord = word.replace(/[^a-zA-Z0-9]/g, "");
         
         if(cleanWord.toLowerCase().includes("battlefield")) {
           emit("battlefield", { text: cleanWord });
         }
         if(cleanWord.toLowerCase().includes("death")) {
           emit("death", { text: cleanWord });
         }
         if(cleanWord.toLowerCase().includes("life")) {
           emit("life", { text: cleanWord });
         }
       });
    }
  },
  function (key, values) {
    var result = { cnt: 0, variations: [] };
    values.forEach(function (v) {
         result.cnt += 1;
         if(v.text.toLowerCase() === key && !result.variations.includes(v.text))
          result.variations.push(v.text)
    });
    result.variations = result.variations.sort()
    return result;
  }
)