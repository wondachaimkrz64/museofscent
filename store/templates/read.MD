 


        <div class="container">
    <br>


        <div class="card mb-3">
            <div class="row g-0">
                <div class="col-md-4">
                    <img src="{{ product.image.url }}" class="img-fluid rounded-start" alt="...">
                </div>
                <div class="col-md-8">
                    <div class="card-body">
                        <center>
                        <h5 class="card-title fs-1 fw-bold">{{ product.name }}</h5>
                        <br>
                        <p class="card-text text-muted">{{ product.description }}</p>
                        {{ product.category }}
                        
                        {% if product.is_sale %}
                        <div class="d-flex justify-content-center small text-warning mb-2">
                                        <div class="bi-star-fill"></div>
                                        <div class="bi-star-fill"></div>
                                        <div class="bi-star-fill"></div>
                                        <div class="bi-star-fill"></div>                               
                                        </div>
                                        <!-- Product price-->
                                        <strike style="margin-right: 6px;">
                                            ₦{{ product.price }}
                                        </strike>
                                        ₦{{ product.sales_price }}
                                        
                        {% else %}
                            <div class="d-flex justify-content-center small text-warning mb-2">
                                <div class="bi-star-fill"></div>
                                <div class="bi-star-fill"></div>
                                <div class="bi-star-fill"></div>
                                <div class="bi-star-fill"></div>
                                <div class="bi-star-fill"></div>
                            </div>

                            ₦{{ product.price }}
                            <br>
                            
                        {% endif %}
                        <br><br>
                        <a href="{% url 'home' %}" class="btn btn-danger">Home</a>
                        <button type="button" value="{{ product.id }}" class="btn btn-danger" id="add-cart">Add To Cart</button>
                    </center>
                    </div>
                </div>
            </div>
        </div>    
    </div>