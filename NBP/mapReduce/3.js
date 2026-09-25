db.cards.mapReduce(
    function () {
      if (this.type) {
        if(this.type.toLowerCase().includes("creature") && this.type.toLowerCase().includes("orc")) {
             emit(this.type, { cnt: 1, noOfSubtypes: this.subtypes ? this.subtypes.length : 0 });
        }
      }
    },
    function (key, values) {
      var result = { count: 0, noOfSubtypes: 0 };
      values.forEach(function (v) {
        result.count += v.cnt;
        result.noOfSubtypes += v.noOfSubtypes;
      });
      return result;
    },
    {
      out: "avgNoOfSubtypes",
      finalize: function (key, val) {
        return { 
          count: val.count, 
          avgNoOfSubtypes: Math.round((val.noOfSubtypes / val.count) * 100) / 100 
        };
      }
    }
  )
  