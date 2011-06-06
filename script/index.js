
var Page; 


Page = new function(){ 
	this.Elements=null, 
	

	this.Init = function(elements){ 
		var caller = this; 
		
		
		this.Elements = elements; 
		
		this.Elements["btnCallToAction"].click( function(e){ 
			caller.ScrollToElement( caller.Elements["pnlInstructions"] ); 
                        e.preventDefault();
		}); 
		
		var i; 
		
		for( i=0;i<500;i++ ){ 
			caller.AddRock(); 
		}
	}, 
	
	this.AddRock = function(){ 
		var newElement; 
		
		
		newElement = $('<div class="rock-dark"></div>'); 
		newElement.css("left", Math.random()*this.Elements["pnlTopsoil"].width()*0.8 ); 
		newElement.css( "top", Math.random()*this.Elements["pnlTopsoil"].height()*0.8); 
		
		this.Elements["pnlTopsoil"].append( newElement ); 
		
		newElement.height( Math.random()*newElement.height() ); 
		newElement.width( Math.random()*newElement.width() ); 
	}, 
	
	
	this.ScrollToElement = function(element){
      $('html,body').animate({scrollTop: element.offset().top},2000);
	}




} 
