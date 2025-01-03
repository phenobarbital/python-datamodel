
from datamodel.jsonld.models import ImageObject

data = """
{
		"@context": "http://schema.org",
		"@type": "Recipe",
		"mainEntityOfPage": "https://www.allrecipes.com/recipe/12682/apple-pie-by-grandma-ople/",
		"name": "Apple Pie by Grandma Ople",
		"image": {
			"@type": "ImageObject",
			"url": "https://imagesvc.meredithcorp.io/v3/mm/image?url=https%3A%2F%2Fimages.media-allrecipes.com%2Fuserphotos%2F736203.jpg",
			"width": null,
			"height": null,
			"caption": "Apple Pie by Grandma Ople"
		},
		"datePublished": "1999-10-08T21:19:13.000Z",
		"description": "This was my grandmother's apple pie recipe.  I have never seen another one quite like it.  It will always be my favorite and has won me several first place prizes in local competitions.  I hope it becomes one of your favorites as well!",
		"prepTime": "P0DT0H30M",
		"cookTime": "P0DT1H0M",
		"totalTime": "P0DT1H30M",
		"recipeYield": "1 - 9 inch pie",
		"recipeIngredient": [
			"1 recipe pastry for a 9 inch double crust pie",
			"½ cup unsalted butter",
			"3 tablespoons all-purpose flour",
			"¼ cup water",
			"½ cup white sugar",
			"½ cup packed brown sugar",
			"8 Granny Smith apples - peeled, cored and sliced"
		],
		"recipeInstructions": [{
				"@type": "HowToStep",
				"text": "Preheat oven to 425 degrees F (220 degrees C). Melt the butter in a saucepan. Stir in flour to form a paste. Add water, white sugar and brown sugar, and bring to a boil. Reduce temperature and let simmer.\n"
			},
			{
				"@type": "HowToStep",
				"text": "Place the bottom crust in your pan. Fill with apples, mounded slightly. Cover with a lattice work crust.  Gently pour the sugar and butter liquid over the crust.  Pour slowly so that it does not run off.\n"
			},
			{
				"@type": "HowToStep",
				"text": "Bake 15 minutes in the preheated oven. Reduce the temperature to 350 degrees F (175 degrees C). Continue baking for 35 to 45 minutes, until apples are soft.\n"
			}
		],
		"recipeCategory": [
			"Dessert Recipes",
			"Pies",
			"Apple Pie Recipes"
		],
		"recipeCuisine": [],
		"author": [{
			"@type": "Person",
			"name": "MOSHASMAMA"
		}],
		"aggregateRating": {
			"@type": "AggregateRating",
			"ratingValue": 4.778342925980458,
			"ratingCount": 14942,
			"itemReviewed": "Apple Pie by Grandma Ople",
			"bestRating": "5",
			"worstRating": "1"
		},
		"nutrition": {
			"@type": "NutritionInformation",
			"calories": "512.2 calories",
			"carbohydrateContent": "67.8 g",
			"cholesterolContent": "30.5 mg",
			"fatContent": "26.7 g",
			"fiberContent": "5 g",
			"proteinContent": "3.6 g",
			"saturatedFatContent": "11.1 g",
			"servingSize": null,
			"sodiumContent": "240.8 mg",
			"sugarContent": "40.3 g",
			"transFatContent": null,
			"unsaturatedFatContent": null
		},
		"review": [{
				"@type": "Review",
				"datePublished": "2009-10-15T16:20:23.473Z",
				"reviewBody": "My words from 2008 still hold true today.  My little grandmother (and I do mean little - not more than 4' 11\") would wonder what all the fuss is about - this is her recipe.  Thanks to all who have commented on this little guardian angel's recipe developed years ago in her kitchen as a treat for my dad who took care of her yard and garden after my grandfather died.  I am still in awe of the number of you that have tried my Grandma Ople's recipe for apple pie and love it so much.  Now that she has been gone almost 15 years there seems to be less and less of her to hold on to and to pass along to her great granchildren (and great-great grandchildren) who will never know her.    Some might say that having originated a delicious apple pie recipe is not much of a legacy, but when I read the reviews and notes of those who have tried her recipe, and the settings and family gatherings at which they have shared her pie, I can truly say that God has worked through my Grandmother to help bring families joy and love.  Thank you all for your comments about my Grandmother's favorite recipe.  Rebecca Clyma Proud Grand-daughter of Grandma Ople",
				"reviewRating": {
					"@type": "Rating",
					"worstRating": "1",
					"bestRating": "5",
					"ratingValue": 5
				},
				"author": {
					"@type": "Person",
					"name": "RCLYMA",
					"image": null,
					"sameAs": "https://www.allrecipes.com/cook/575406/"
				}
			},
			{
				"@type": "Review",
				"datePublished": "2003-11-06T18:41:52.42Z",
				"reviewBody": "A++ Decadently Delicious!  Ive tried many recipes from this site, all of them pleasing.  But this is the first time I've ever been so inspired by one to write a review!  You wont find a better recipe for apple pie.  \r\n\r\nI read every review for people's advice before starting, and did make a few adjustments to the original.  Some mentioned granny smith apples were too tart.  Stick with the recipe on that one.  I added a teaspoon of cinnamon, a good dash of nutmeg and a tablespoon of vanilla to the syrup prior to simmering (compensate for adding the vanilla by omiting a tablespoon of that 1/4 cup of water).  Next, definately mix the syrup with the apples rather than trying to pour into the pie (save enough to glaze top crust).  Do use a 9\" glass pie pan to avoid spillage.  Use the middle shelf in the oven (so top crust doesnt brown too fast).  And last but not least, I did the lattice top crust, and it turned out picture perfect, but im convinced that using a complete top crust with designer slits cut into it would turn out just as beautifully.  Whatever you decide to do with the top crust, just remember the syrup you saved to glaze the top with needs to still be HOT or it will thicken up on you, so have your plan together and move quickly.    \r\n\r\nIn all, this recipe is amazing.  I will make this for anyone I am trying to impress!  Three cheers for Grandma Opal and family.",
				"reviewRating": {
					"@type": "Rating",
					"worstRating": "1",
					"bestRating": "5",
					"ratingValue": 5
				},
				"author": {
					"@type": "Person",
					"name": "SCIOTA",
					"image": null,
					"sameAs": "https://www.allrecipes.com/cook/515622/"
				}
			},
			{
				"@type": "Review",
				"datePublished": "2008-02-28T13:22:19.423Z",
				"reviewBody": "Believe the hype.\nI made this for the first time for a dinner party I had last week - mostly because I wanted to see what all the fuss was about. And it did not disappoint. Women were begging for the recipe. Men were saying it was the best apple pie they had ever tasted. There were riots over who was going to get the last piece.\n\nI followed everyone's suggestions here... prepared the lattice ahead of time and kept it in the fridge til ready... mixed a tsp of cinnamon to the butter and sugar mixture... brushed egg whites on bottom crust to keep from getting soggy... poured 2/3 of mixture over the apples first, then the rest over the top of the crust... baked at 350F for the whole time to avoid burnt topping... put baking tray in bottom of the over to catch the drips.  \n\nHence forth I am eschewing all other apple pie recipes. Truly spectacular.",
				"reviewRating": {
					"@type": "Rating",
					"worstRating": "1",
					"bestRating": "5",
					"ratingValue": 5
				},
				"author": {
					"@type": "Person",
					"name": "wee red",
					"image": null,
					"sameAs": "https://www.allrecipes.com/cook/990276/"
				}
			},
			{
				"@type": "Review",
				"datePublished": "2005-10-24T19:10:33Z",
				"reviewBody": "WONDERFUL PIE!!! I heeded other's warnings and suggestions on this one. 1. I baked the pie at 350 degreees for the entire time to minimize scorching.\r\n2. I added 2 tablespoons flour and 1 tablespoon cornstarch to the syrup mixture. I also eliminated the water from the syrup mixture which made the pie very thick and gel-like. I also added cinnamon, cloves, allspice, and nutmeg to the syrup.\r\n3. I mixed half of the syrup with the apples themselves before putting in the pie crust.\r\n4. The syrup crystalizes very easily, so I made half of the syrup to mix in with the apples. Then I was able to take my time making my lattice crust and garnishes. Then, I mixed up the rest of the syrup and brushed it on the top of the pie.\r\n5. About 10 minutes before the pie was done (about 50 minutes had elapsed), I brushed the pie with a little milk and sprinkled the top with sugar and cinnamon.\r\n6. After making it again, I served it warm. NOT A GOOD IDEA! It was very runny. The first time  allowed it to sit overnight and warmed it slightly in the microwave before serving.\r\nI AM SO HAPPY I FOUND THIS RECIPE. I even entered it in a local pie-making contest and out of 108 entries, I recieved the grand prize and $1,000! So this is truly my award-winning pie!!! Thanks so much for the recipe! It's a keeper!",
				"reviewRating": {
					"@type": "Rating",
					"worstRating": "1",
					"bestRating": "5",
					"ratingValue": 5
				},
				"author": {
					"@type": "Person",
					"name": "Leslie Sullivan",
					"image": null,
					"sameAs": "https://www.allrecipes.com/cook/995256/"
				}
			},
			{
				"@type": "Review",
				"datePublished": "2003-11-06T18:46:18.89Z",
				"reviewBody": "Delicious!  It came out perfect, though I did not lattice the crust.  I just put some decorative cuts into it...obviously won't change the taste,  just the look.  (I used \"Earthquake Pie Crust\" from this site) And after reading *many* of the reviews, I think the slight changes I made to the recipe made it easy to make, I knew what to expect, and not only did it not bubble over at all, it didn't even get my pan and foil dirty that I had underneath it.  This is what I did: used 4 big Red Delicious apples, and they piled up in a good mound.  Granny Smith would have made it too tart for me.  I don't know how anyone used all 8 unless they were the size of plums. ...used a glass pie dish; they are bigger and deeper than the tin ones.  ...put a pan lined with foil underneath it before baking so if any juice did run off, it wouldn't get anything dirty. ...added 1 tsp cinnamon, 1/2 tsp nutmeg, 1 tbs vanilla (and also took 1 tbs of water out of the 1/4 cup). ...lastly, I added 3/4 of the caramel to the apples prior to putting them into the pie crust. The caramel will seem thick, like it doesn't run down the apples well.  But sugar helps fruit create its own juices...it will make more juice while it is baking.  Just mix it all well.  My caramel was not runny & did not bubble over during baking.  The little changes I made after reading the reviews helped to avoid mistakes others made. Thanks!",
				"reviewRating": {
					"@type": "Rating",
					"worstRating": "1",
					"bestRating": "5",
					"ratingValue": 5
				},
				"author": {
					"@type": "Person",
					"name": "TARA1972",
					"image": null,
					"sameAs": "https://www.allrecipes.com/cook/577349/"
				}
			},
			{
				"@type": "Review",
				"datePublished": "2008-01-14T08:05:14.78Z",
				"reviewBody": "I am very disappointed by the outcome. I followed the directions exactly, except mixed the sauce with the apples. The inside was so runny, and never thickened up. I trusted the rating, but don't let it fool you. I put a lot of time and effort into this apple pie, and I can't believe it came out like this, when everyone was raving about how good it is. Does anyone have any comments about what I may have did wrong, because I read over the directions again, and I did everything right. I guess I'll keep looking for that perfect recipe. Very disappointed!",
				"reviewRating": {
					"@type": "Rating",
					"worstRating": "1",
					"bestRating": "5",
					"ratingValue": 1
				},
				"author": {
					"@type": "Person",
					"name": "Lori Isenberg",
					"image": null,
					"sameAs": "https://www.allrecipes.com/cook/2410923/"
				}
			},
			{
				"@type": "Review",
				"datePublished": "2003-09-28T02:42:12.967Z",
				"reviewBody": "This past weekend 9/6 - 9/8/02 I made this pie for the Hillsboro County Fair in New Hampshire and won the First Prize Blue Ribbon.  I hadn't even tasted the pie, but felt confident enough to make it after reading all of the wonderful reviews.  I did add 1 tsp. of vanilla and 1 tsp. of cinnamon, because around here, cinnamon is a must for apple pie, and vanilla adds a wonderful flavor to just about everything.  I didn't make the latice crust...I added all of the syrup to the apples and mixed them well before placing onto the bottom crust, but I did leave a little extra to brush on the top crust.  You must try this recipe...it is delicious!!!!!!!  Thanks for helping me win the Blue Ribbon!!!!!!!!!",
				"reviewRating": {
					"@type": "Rating",
					"worstRating": "1",
					"bestRating": "5",
					"ratingValue": 5
				},
				"author": {
					"@type": "Person",
					"name": "Carol Dougherty",
					"image": null,
					"sameAs": "https://www.allrecipes.com/cook/468021/"
				}
			},
			{
				"@type": "Review",
				"datePublished": "2003-09-28T02:41:37.92Z",
				"reviewBody": "I have made hundreds of apple pies in my life and I believe that this is my favorite, although I changed a few things. I increased the suger, brown and white, by a half a cup, put in fresh ground cinnamon and nutmeg and vanilla. I also added a tablespoon of corn starch to the syrup mixture...it thickens the sauce better. My husband can't wait for this pie to bake. It is truely a great pie. Adding a little extra to this recipe makes it a real show stopper and my most requested pie.",
				"reviewRating": {
					"@type": "Rating",
					"worstRating": "1",
					"bestRating": "5",
					"ratingValue": 5
				},
				"author": {
					"@type": "Person",
					"name": "GRACIEMARIE",
					"image": null,
					"sameAs": "https://www.allrecipes.com/cook/728353/"
				}
			},
			{
				"@type": "Review",
				"datePublished": "2007-02-12T01:56:28.31Z",
				"reviewBody": "There's no need to keep looking around for an apple pie recipe.  This one is delicious.  I modified it slightly based on other reviews. Use 6 apples (instead of 8) and you'll have plenty. Instead of pouring the sauce on top of the pie crust, I just mixed it in with the apples.  Additionally, I added\n1 tsp. cinnamon, 1/2 tsp. nutmeg and 1 tsp. vanilla to apples.  To make my life easier, I used the Pilsbury ready-made pie crust and I didn't do the lattice top.  Instead, I just made slits in the pie crust, brushed a thin coating of milk over the top and sprinkled with sugar.  Don't forget to put a cookie sheet under the pie dish when baking--it will overflow!  Lastly, I thought my apples turned out perfectly extending the cooking time at 350 to 50 minutes.  Please enjoy this recipe!!!",
				"reviewRating": {
					"@type": "Rating",
					"worstRating": "1",
					"bestRating": "5",
					"ratingValue": 5
				},
				"author": {
					"@type": "Person",
					"name": "Elizabeth Purcell",
					"image": null,
					"sameAs": "https://www.allrecipes.com/cook/1977395/"
				}
			}
		],
		"video": {
			"@context": "http://schema.org",
			"@type": "VideoObject",
			"name": "Apple Pie by Grandma Ople",
			"description": "Learn how to make Grandma Ople's apple pie.",
			"uploadDate": "2012-05-09T09:07:12.148Z",
			"duration": "PT4M4.744S",
			"thumbnailUrl": "https://imagesvc.meredithcorp.io/v3/mm/image?url=https%3A%2F%2Fcf-images.us-east-1.prod.boltdns.net%2Fv1%2Fstatic%2F1033249144001%2F571fbd8d-66c7-4521-b002-cbb53ace86e9%2Ff253b5d1-edaf-4dc7-8f0c-954a4259d97f%2F160x90%2Fmatch%2Fimage.jpg",
			"publisher": {
				"@type": "Organization",
				"name": "Allrecipes",
				"url": "https://www.allrecipes.com",
				"logo": {
					"@type": "ImageObject",
					"url": "https://www.allrecipes.com/img/logo.png",
					"width": 209,
					"height": 60
				},
				"sameAs": [
					"https://www.facebook.com/allrecipes",
					"https://twitter.com/Allrecipes",
					"https://www.pinterest.com/allrecipes/",
					"https://www.instagram.com/allrecipes/"
				]
			},
			"embedUrl": "https://players.brightcove.net/1033249144001/default_default/index.html?videoId=1629100183001"
		}
	}
"""  # noqa


img = ImageObject(name="a Mexico Beach", url="mexico-beach.jpg", caption="Sunny, sandy beach.")
print(img.to_html(top_level=True))
