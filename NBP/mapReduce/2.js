db.nobelprizes.mapReduce(
    function () {
      if (this.laureates)
        emit(this.category, { sum: this.laureates.length, cnt: 1 });
    },
    function (key, values) {
      var result = { sum: 0, cnt: 0 };
      values.forEach(function (v) {
        result.sum += v.sum;
        result.cnt += v.cnt;
      });
      return result;
    },
    {
      out: "avg",
      finalize: function (key, val) {
        return { avg: Math.round((val.sum / val.cnt)* 100) / 100 };
      }
    }
  )