import { session } from "@web/session";


setInterval(()=>{

    console.log(this)

    var name_div=document.getElementsByClassName('o_last_breadcrumb_item');

    if(name_div[0]){
        if(name_div[0].children[0]){
            if(name_div[0].children[0].innerText=='September Requests'){

                    var canban_div=document.getElementsByClassName('o_draggable');

                    if(canban_div){
                             Array.from(canban_div).forEach(el => {

                                  el.classList.remove('o_draggable');

                                });
                    }

                    var facets=document.getElementsByClassName('o_facet_value');

                    if(facets){

                        Array.from(facets).forEach(el=>{

                            if(el.innerText=='ჩემი მოთხოვნები'){
                                var parent_div=el.parentElement;
                                parent_div.style.pointerEvents='none';
                            }

                        });

                    }

                    var dropdownitems=document.getElementsByClassName('o-dropdown-item');

                    if(dropdownitems){

                        Array.from(dropdownitems).forEach(el=>{

                            if(el.innerText=='ჩემი მოთხოვნები'){
                                if(el.classList.contains("selected")){
                                    el.style.pointerEvents='none';
                                }
                            }

                        });

                    }

            }else if(name_div[0].children[0].innerText=='Inventory Requests'){

                var canban_div=document.getElementsByClassName('o_draggable');

                if(canban_div){
                    Array.from(canban_div).forEach(el => {

                        el.classList.remove('o_draggable');

                    });
                }

                var facets=document.getElementsByClassName('o_facet_value');

                if(facets){

                    Array.from(facets).forEach(el=>{

                        if(el.innerText=='ჩემი მოთხოვნები'){
                            var parent_div=el.parentElement;
                            parent_div.style.pointerEvents='none';
                        }

                    });

                }

                var dropdownitems=document.getElementsByClassName('o-dropdown-item');

                if(dropdownitems){

                    Array.from(dropdownitems).forEach(el=>{

                        if(el.innerText=='ჩემი მოთხოვნები'){
                            if(el.classList.contains("selected")){
                                el.style.pointerEvents='none';
                            }
                        }

                    });

                }

            }
        }
    }

},100);