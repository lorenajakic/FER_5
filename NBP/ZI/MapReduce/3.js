db.cards.mapReduce(
    `function() {
        if (this.cmc < 10 && this.colors && this.colors.length > 1) {
			emit(this.cmc, {types: this.types || [], subtypes: this.subtypes || []});		
		}
    }`,   
    `function(key, values) {
        var rv = {types: [], subtypes: []};
        values.forEach( function(value) {
			rv.types = rv.types.concat(value.types);
            rv.subtypes = rv.subtypes.concat(value.subtypes);
        });
        // ovaj distinct se može staviti i u finalize, ali čini mi se da je preformansno bolje ovdje:
        rv.types = rv.types.filter((obj, idx, arr) => (
          arr.findIndex((o) => o === obj) === idx
        ));
		rv.subtypes = rv.subtypes.filter((obj, idx, arr) => (
          arr.findIndex((o) => o === obj) === idx
        ));
        return rv;  
    }`,   
    { 
        finalize: `
		function (key, value) {
            return {
				types: value.types.sort(), 
				distSubtypesCount: value.subtypes.length
			};
       	}`
    }
);