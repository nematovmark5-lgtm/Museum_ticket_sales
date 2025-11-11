const multipliers = {
    'Стандартный': 1.0,
    'Льготный': 0.6,
    'Детский': 0.4,
    'Студенческий': 0.5,
    'Пенсионный': 0.4
};

function scrollToTicketSection() {
    const ticketSection = document.querySelector('.ticket-section');
    if (ticketSection) {
        ticketSection.scrollIntoView({ 
            behavior: 'smooth',
            block: 'start'
        });
    }
}

function updateTicketSectionVisibility() {
    const ticketBuySection = document.querySelector('.ticket-section .ticket-card');
    const authRequiredSection = document.getElementById('ticket-auth-required');
    
    if (currentUser) {
        if (ticketBuySection) ticketBuySection.style.display = 'block';
        if (authRequiredSection) authRequiredSection.style.display = 'none';
    } else {
        if (ticketBuySection) ticketBuySection.style.display = 'none';
        if (authRequiredSection) authRequiredSection.style.display = 'block';
    }
}

let currentUser = null;
let currentMuseumPrice = 0;
let currentMuseumId = null;
let currentTicketCategory = 'Стандартный';

const API_BASE_URL = 'http://localhost:8002';

let currentImageIndex = 0;
let selectedDateSlot = null;
let selectedTimeSlot = null;

let slotsInterval = null;
let currentAvailableTickets = 0;

let currentSlide = 0;
const slides = document.querySelectorAll('.slide');
const indicators = document.querySelectorAll('.slider-indicators button');
const totalSlides = slides.length;

function showSlide(index) {
    slides.forEach(slide => {
        slide.classList.remove('active');
    });
    
    slides[index].classList.add('active');
    
    indicators.forEach((indicator, i) => {
        if (i === index) {
            indicator.classList.add('active');
        } else {
            indicator.classList.remove('active');
        }
    });
    
    currentSlide = index;
}

function nextSlide() {
    currentSlide = (currentSlide + 1) % totalSlides;
    showSlide(currentSlide);
}

if (slides.length > 0) {
    setInterval(nextSlide, 5000);
    
    indicators.forEach((indicator, index) => {
        indicator.addEventListener('click', () => {
            showSlide(index);
        });
    });
}

document.querySelector('.hero-content button')?.addEventListener('click', function() {
    document.querySelector('.museums-section').scrollIntoView({ behavior: 'smooth' });
});

document.querySelector('.muse')?.addEventListener('click', function(e) {
    e.preventDefault();
    document.querySelector('.museums-section').scrollIntoView({ behavior: 'smooth' });
});

const museumData = {
    'modern-art': {
        title: 'Музей современного искусства',
        tag: 'Искусство',
        subtitle: 'Уникальная коллекция современного искусства и интерактивные инсталляции',
        description: 'Один из крупнейших музеев современного искусства в регионе. Здесь представлены работы ведущих художников XX и XXI века, включая живопись, скульптуру, инсталляции и медиа-арт. Музей регулярно проводит временные выставки, мастер-классы и образовательные программы. Основанный в 1995 году, музей стал важным центром культурной жизни города. В его постоянной коллекции представлено более 5000 произведений искусства, включая работы как российских, так и зарубежных художников.',
        price: 500,
        images: [
            'https://cdn.poehali.dev/projects/7e7c7725-c77f-4448-88a5-a4f85ace8939/files/91a270d3-1185-489d-bbce-0e2a52ce896b.jpg',
            'https://upload.wikimedia.org/wikipedia/commons/thumb/2/25/Museu_de_Arte_Contemporânea_de_Niterói.jpg/960px-Museu_de_Arte_Contemporânea_de_Niterói.jpg',
            'https://img.topky.sk/cestovky/900px/1114322.jpg/zaujimavosti-den-Europa.jpg'
        ],
        address: 'ул. Искусств, д. 10',
        hours: 'Круглосуточно 10:00-18:00'
    },
    'history': {
        title: 'Исторический музей',
        tag: 'История',
        subtitle: 'Погрузитесь в историю через уникальные артефакты и экспозиции',
        description: 'Основанный в 1895 году, Исторический музей хранит богатейшую коллекцию артефактов, отражающих историю региона с древнейших времен до наших дней. В музее представлены уникальные археологические находки, документы, оружие и предметы быта разных эпох. Особой гордостью музея является коллекция средневекового оружия и доспехов, а также реконструкции древнего поселения в натуральную величину.',
        price: 400,
        images: [
            'https://cdn.poehali.dev/projects/7e7c7725-c77f-4448-88a5-a4f85ace8939/files/629ca2c2-81fd-419a-b2e4-63185088c637.jpg',
            'https://avatars.dzeninfra.ru/get-zen_doc/271828/pub_676c0ac2db74cf0b2a069b75_676c3a53db74cf0b2a5c5801/scale_1200',
            'https://i.pinimg.com/736x/0d/0d/48/0d0d48952fbd8b2b305663ec5ec55688.jpg'
        ],
        address: 'ул. Историческая, д. 25',
        hours: 'Круглосуточно 10:00-18:00'
    },
    'science': {
        title: 'Музей науки и техники',
        tag: 'Наука',
        subtitle: 'Интерактивные экспонаты, демонстрации и научные эксперименты',
        description: 'Интерактивный музей, где можно не только смотреть, но и трогать экспонаты. Посетители могут провести физические эксперименты, познакомиться с принципами работы различных механизмов и даже поуправлять роботами. Музей особенно популярен среди детей и подростков. В экспозиции представлены достижения науки от простых механизмов до современных технологий, включая разделы по робототехнике, астрономии и биологии.',
        price: 450,
        images: [
            'https://cdn.poehali.dev/projects/7e7c7725-c77f-4448-88a5-a4f85ace8939/files/0a851476-2d06-4639-94a8-e569a11c7574.jpg',
            'https://cdn.culture.ru/images/d520bfaf-5d0e-50f8-8d58-86c26b6afbee',
            'https://life-globe.com/image/cache/catalog/russia/sankt-peterburg/petropavlovskaya-krepost/muzej-nauki-i-tehniki/muzej-nauki-i-tehniki-1/muzej-nauki-i-tehniki-petropavlovskaya-krepost-915x610.jpg'
        ],
        address: 'пр. Науки, д. 15',
        hours: 'Круглосуточно 10:00-18:00'
    },
    'gallery': {
        title: 'Художественная галерея',
        tag: 'Искусство',
        subtitle: 'Произведения классического и современного изобразительного искусства',
        description: 'Галерея представляет собой уникальное собрание произведений изобразительного искусства от классики до современности. В коллекции представлены работы известных русских и зарубежных художников, а также регулярно проводятся выставки современных авторов. Особенностью галереи является интерактивная экспозиция, позволяющая посетителям глубже понять творческий процесс художников разных эпох.',
        price: 450,
        images: [
            'https://cdn.poehali.dev/projects/7e7c7725-c77f-4448-88a5-a4f85ace8939/files/08e35c00-8b7a-426c-8366-025fa7c26fa9.jpg',
            'https://avatars.mds.yandex.net/i?id=291deeebd5d7ebad3fcb276740edabf8_l-9197564-images-thumbs&n=13',
            'https://vedomostiural.ru/uploadedFiles/newsimages/big/photo_2023-04-19_14-15-03.jpg'
        ],
        address: 'ул. Художественная, д. 8',
        hours: 'Круглосуточно 10:00-18:00'
    },
    'ethno': {
        title: 'Этнографический музей',
        tag: 'Культура',
        subtitle: 'Богатая коллекция традиционных костюмов, предметов быта и ремесел народов мира',
        description: 'Музей посвящен культуре и быту народов разных стран. В экспозиции представлены традиционные костюмы, украшения, предметы домашнего обихода, орудия труда и произведения народного искусства. Особый интерес представляет коллекция традиционных музыкальных инструментов. Музей проводит мастер-классы по народным ремеслам и фольклорные концерты, позволяющие полностью погрузиться в культуру разных народов.',
        price: 350,
        images: [
            'https://fs.znanio.ru/d5af0e/6f/9a/724f0e997f478c5f0f0f472637e156e7a3.jpg',
            'https://ethnomuseum.ru/images/NIWPOSETITLU/SOBITIA/2021/German/952.jpg',
            'https://r1.nubex.ru/s998-600/f1865_01/IMG_2431.JPG'
        ],
        address: 'ул. Этнографическая, д. 12',
        hours: 'Круглосуточно 10:00-18:00'
    },
    'nature': {
        title: 'Музей естественной истории',
        tag: 'Природа',
        subtitle: 'Увлекательное путешествие в мир природы: от динозавров до современных экосистем',
        description: 'Музей предлагает уникальную возможность познакомиться с разнообразием жизни на Земле. В экспозиции представлены скелеты динозавров, коллекции минералов, чучела животных и интерактивные модели экосистем. Особой популярностью пользуется зал с макетом пещеры первобытного человека. Музей активно использует современные технологии, включая VR-экскурсии по доисторическим ландшафтам.',
        price: 420,
        images: [
            'https://res.klook.com/image/upload/c_fill,w_627,h_470/q_80/w_80,x_15,y_15,g_south_west,l_Klook_water_br_trans_yhcmh3/activities/bjwgmtlezhj76wkid5lq.jpg',
            'https://cdn.culture.ru/images/c13b7fb7-c0d3-521e-9283-a73a47641ee6',
            'https://i.pinimg.com/originals/9a/0b/ad/9a0badeb44fb220900feee928e8e77d8.jpg'
        ],
        address: 'ул. Природная, д. 5',
        hours: 'Круглосуточно 10:00-18:00'
    }
};

function showAuthModal() {
    document.getElementById('auth-modal').style.display = 'flex';
}

function hideAuthModal() {
    document.getElementById('auth-modal').style.display = 'none';
}

function switchAuthTab(tab) {
    document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.auth-tab').forEach(t => {
        if (t.textContent === (tab === 'login' ? 'Войти' : 'Регистрация')) {
            t.classList.add('active');
        }
    });
    
    if (tab === 'login') {
        document.getElementById('login-form').style.display = 'block';
        document.getElementById('register-form').style.display = 'none';
    } else {
        document.getElementById('login-form').style.display = 'none';
        document.getElementById('register-form').style.display = 'block';
    }
}

async function login() {
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    
    if (!username || !password) {
        showMessage('Пожалуйста, заполните все поля');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/visitors/login/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                login: username,
                password: password
            })
        });
        
        if (response.ok) {
            const user = await response.json();
            currentUser = user;
            
            saveUserToStorage(user);
            
            updateUI();
            hideAuthModal();
            showMessage('Вы успешно вошли в систему!');

            updateTicketSectionVisibility();
            
            document.getElementById('login-username').value = '';
            document.getElementById('login-password').value = '';
        } else {
            const errorData = await response.json();
            showMessage('Неверный логин или пароль');
        }
    } catch (error) {
        console.error('Ошибка сети:', error);
        showMessage('Ошибка подключения к серверу');
    }
}

async function register() {
    const userData = {
        login: document.getElementById('register-username').value,
        password: document.getElementById('register-password').value,
        name: document.getElementById('register-name').value,
        surname: document.getElementById('register-surname').value,
        phone: document.getElementById('register-phone').value
    };
    
    if (!userData.login || !userData.password || !userData.name || !userData.phone) {
        showMessage('Пожалуйста, заполните все обязательные поля');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/visitors/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(userData)
        });
        
        if (response.ok) {
            const newUser = await response.json();
            currentUser = newUser;
            
            saveUserToStorage(newUser);
            
            updateUI();
            hideAuthModal();
            showMessage('Вы успешно зарегистрировались! Теперь можете покупать билеты.');

            updateTicketSectionVisibility();
            
            document.getElementById('register-username').value = '';
            document.getElementById('register-password').value = '';
            document.getElementById('register-name').value = '';
            document.getElementById('register-surname').value = '';
            document.getElementById('register-phone').value = '';
        } else {
            const errorData = await response.json();
            showMessage('Ошибка регистрации: ' + errorData.detail);
        }
    } catch (error) {
        console.error('Ошибка сети:', error);
        showMessage('Ошибка подключения к серверу');
    }
}

function logout() {
    currentUser = null;
    removeUserFromStorage();
    updateUI();
    showMessage('Вы вышли из системы');

    updateTicketSectionVisibility();
    
    document.getElementById('my-tickets-section').style.display = 'none';
    document.body.style.overflow = 'auto';
}

function checkAuth() {
    const savedUser = getUserFromStorage();
    if (savedUser) {
        currentUser = savedUser;
        console.log('✅ Пользователь восстановлен из localStorage:', currentUser.name);
        showMessage(`С возвращением, ${currentUser.name}!`);
    }
    updateUI();
    
    setTimeout(updateTicketSectionVisibility, 100);
}

function updateUI() {
    const authNav = document.getElementById('auth-nav');
    const userNav = document.getElementById('user-nav');
    
    if (currentUser && authNav && userNav) {
        authNav.style.display = 'none';
        userNav.style.display = 'flex';
        console.log('✅ Интерфейс обновлен: пользователь авторизован');
    } else if (authNav && userNav) {
        authNav.style.display = 'flex';
        userNav.style.display = 'none';
        console.log('✅ Интерфейс обновлен: пользователь не авторизован');
    }
}

function showMessage(message) {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--primary);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        z-index: 10000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentNode) {
            document.body.removeChild(notification);
        }
    }, 3000);
}

function showImage(index) {
    if (!currentMuseumId) return;
    
    const museum = museumData[currentMuseumId];
    currentImageIndex = index;
    document.getElementById('main-image').src = museum.images[currentImageIndex];
    
    updateThumbnails();
}

function updateThumbnails() {
    const thumbnails = document.querySelectorAll('#thumbnail-container button');
    thumbnails.forEach((thumb, i) => {
        if (i === currentImageIndex) {
            thumb.classList.add('ring-4', 'ring-primary');
            thumb.classList.remove('opacity-70');
        } else {
            thumb.classList.remove('ring-4', 'ring-primary');
            thumb.classList.add('opacity-70');
        }
    });
}

function nextImage() {
    if (!currentMuseumId) return;
    
    const museum = museumData[currentMuseumId];
    currentImageIndex = (currentImageIndex + 1) % museum.images.length;
    showImage(currentImageIndex);
}

function prevImage() {
    if (!currentMuseumId) return;
    
    const museum = museumData[currentMuseumId];
    currentImageIndex = (currentImageIndex - 1 + museum.images.length) % museum.images.length;
    showImage(currentImageIndex);
}

function increaseTickets() {
    const ticketInput = document.getElementById('tickets');
    let currentValue = parseInt(ticketInput.value);
    
    if (currentValue >= 10) {
        showMessage('Нельзя заказать больше 10 билетов за один раз');
        return;
    }
    
    if (selectedDateSlot && selectedTimeSlot) {
        if (currentValue >= currentAvailableTickets) {
            showMessage(`В выбранном слоте доступно только ${currentAvailableTickets} билетов. Выберите другой слот или уменьшите количество билетов.`);
            return;
        }
    }
    
    currentValue++;
    ticketInput.value = currentValue;
    
    ticketCategories.push('Стандартный');
    
    updateTicketCategoriesUI();
    updateTotal();
}

function decreaseTickets() {
    const ticketInput = document.getElementById('tickets');
    let currentValue = parseInt(ticketInput.value);
    if (currentValue > 1) {
        currentValue--;
        ticketInput.value = currentValue;
        
        ticketCategories.pop();
        
        updateTicketCategoriesUI();
        updateTotal();
    }
}

function updateTicketPrice() {
    
    updateTotal();
}

function updateTotal() {
    const ticketInput = document.getElementById('tickets');
    if (!ticketInput) return;
    
    const ticketCount = parseInt(ticketInput.value);
    let totalPrice = 0;
    
    if (!ticketCategories || ticketCategories.length === 0) {
        ticketCategories = ['Стандартный'];
    }
    
    const detailsContainer = document.getElementById('ticket-details-container');
    if (!detailsContainer) return;
    
    let detailsHTML = '';
    
    ticketCategories.forEach((category, index) => {
        const multiplier = multipliers[category] || 1.0;
        const discountedPrice = Math.round(currentMuseumPrice * multiplier);
        totalPrice += discountedPrice;
        
        detailsHTML += `
            <div class="summary-row ticket-detail-row">
                <span class="text-muted-foreground">Билет №${index + 1} (${category}): </span>
                <span class="font-semibold">
                    ${currentMuseumPrice}₽ ${category !== 'Стандартный' ? `→ <span style="font-size: 20px; color: green;">${discountedPrice}₽</span>` : ''}
                </span>
            </div>
        `;
    });
    
    detailsHTML += `
        <div class="summary-row">
            <span class="text-muted-foreground">Количество билетов:</span>
            <span class="font-semibold">${ticketCount}</span>
        </div>
    `;
    
    detailsContainer.innerHTML = detailsHTML;
    
    const totalPriceElement = document.getElementById('total-price');
    if (totalPriceElement) {
        totalPriceElement.textContent = totalPrice + '₽';
    }
}

function openMuseumDetail(museumId) {
    currentMuseumId = museumId;
    
    updateMuseumDescription(museumId);
    document.getElementById('museum-detail').style.display = 'block';
    document.body.style.overflow = 'hidden';
    
    currentImageIndex = 0;
    showImage(currentImageIndex);
    
    selectedDateSlot = null;
    selectedTimeSlot = null;
    currentAvailableTickets = 0;
    
    document.getElementById('tickets').value = 1;
    ticketCategories = ['Стандартный'];
    
    updateDateSelection();
    generateDateSlots();
    updateTicketCategoriesUI();
    updateTotal();
    
    updateTicketSectionVisibility();
    
    startSlotsUpdateInterval();
}

function closeMuseumDetail() {
    document.getElementById('museum-detail').style.display = 'none';
    document.body.style.overflow = 'auto';
    currentMuseumId = null;
    
    stopSlotsUpdateInterval();
}

function updateMuseumDescription(museumId) {
    const museum = museumData[museumId];
    if (!museum) return;

    const categoryTag = document.querySelector('.museum-description .category-tag');
    const title = document.querySelector('.museum-description h1');
    const subtitle = document.querySelector('.museum-description .text-xl');
    const description = document.querySelector('.museum-description .text-lg');
    const price = document.querySelector('.detail-item .text-2xl');
    const address = document.querySelector('.detail-item:nth-child(2) .text-muted-foreground');
    const hours = document.querySelector('.detail-item:nth-child(1) .text-muted-foreground');
    
    if (categoryTag) categoryTag.textContent = museum.tag;
    if (title) title.textContent = museum.title;
    if (subtitle) subtitle.textContent = museum.subtitle;
    if (description) description.textContent = museum.description;
    if (price) price.textContent = museum.price + '₽';
    if (address) address.textContent = museum.address;
    if (hours) hours.textContent = museum.hours;
    
    currentMuseumPrice = museum.price;
    
    updateGallery(museum.images);
    
    document.getElementById('tickets').value = 1;
    updateTicketPrice();
    updateTotal();
}

function updateGallery(images) {
    const mainImage = document.getElementById('main-image');
    const thumbnailContainer = document.getElementById('thumbnail-container');
    
    if (mainImage) mainImage.src = images[0];
    
    if (thumbnailContainer) {
        thumbnailContainer.innerHTML = '';
        
        images.forEach((image, index) => {
            const button = document.createElement('button');
            button.className = `relative h-32 rounded-lg overflow-hidden transition-all ${index === 0 ? 'ring-4 ring-primary' : 'opacity-70 hover:opacity-100'}`;
            button.onclick = () => showImage(index);
            
            const img = document.createElement('img');
            img.src = image;
            img.alt = `Изображение ${index + 1}`;
            img.className = 'w-full h-full object-cover';
            
            button.appendChild(img);
            thumbnailContainer.appendChild(button);
        });
    }
}


async function getAvailableTimeSlots(museumCode, date) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/time-slots/${museumCode}/${date}`);
        if (response.ok) {
            return await response.json();
        }
        return [];
    } catch (error) {
        console.error('Ошибка при получении слотов:', error);
        return [];
    }
}


function setupPaymentValidation() {
    const cardNumberInput = document.getElementById('card-number');
    const cardExpiryInput = document.getElementById('card-expiry');
    const cardCvvInput = document.getElementById('card-cvv');
    const cardHolderInput = document.getElementById('card-holder');

    if (cardNumberInput) {
        cardNumberInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\s+/g, '').replace(/[^0-9]/gi, '');
            let formattedValue = '';
            
            for (let i = 0; i < value.length; i++) {
                if (i > 0 && i % 4 === 0) {
                    formattedValue += ' ';
                }
                formattedValue += value[i];
            }
            
            e.target.value = formattedValue.substring(0, 19);
        });
    }

    if (cardExpiryInput) {
        cardExpiryInput.addEventListener('input', function(e) {
            let value = e.target.value.replace(/[^0-9]/g, '');
            
            if (value.length >= 2) {
                value = value.substring(0, 2) + '/' + value.substring(2);
            }
            
            e.target.value = value.substring(0, 5);
        });
    }

    if (cardCvvInput) {
        cardCvvInput.addEventListener('input', function(e) {
            e.target.value = e.target.value.replace(/[^0-9]/g, '').substring(0, 4);
        });
    }

    if (cardHolderInput) {
        cardHolderInput.addEventListener('input', function(e) {
            e.target.value = e.target.value.replace(/[^a-zA-Zа-яА-Я\s]/g, '').toUpperCase();
        });
    }
}

function validatePaymentForm() {
    const cardNumber = document.getElementById('card-number').value.replace(/\s/g, '');
    const cardExpiry = document.getElementById('card-expiry').value;
    const cardCvv = document.getElementById('card-cvv').value;
    const cardHolder = document.getElementById('card-holder').value.trim();

    let isValid = true;
    let errorMessage = '';

    if (!cardNumber || cardNumber.length !== 16 || !/^\d+$/.test(cardNumber)) {
        isValid = false;
        errorMessage = 'Введите корректный номер карты (16 цифр)';
        highlightField('card-number', false);
    } else {
        highlightField('card-number', true);
    }

    if (!cardExpiry || !/^\d{2}\/\d{2}$/.test(cardExpiry)) {
        isValid = false;
        errorMessage = 'Введите срок действия в формате ММ/ГГ';
        highlightField('card-expiry', false);
    } else {
        const [month, year] = cardExpiry.split('/');
        const monthNum = parseInt(month);
        const yearNum = parseInt('20' + year);
        const currentDate = new Date();
        const currentYear = currentDate.getFullYear();
        const currentMonth = currentDate.getMonth() + 1;

        if (monthNum < 1 || monthNum > 12) {
            isValid = false;
            errorMessage = 'Месяц должен быть от 01 до 12';
            highlightField('card-expiry', false);
        } else if (yearNum < currentYear || (yearNum === currentYear && monthNum < currentMonth)) {
            isValid = false;
            errorMessage = 'Срок действия карты истек';
            highlightField('card-expiry', false);
        } else {
            highlightField('card-expiry', true);
        }
    }

    if (!cardCvv || cardCvv.length < 3 || cardCvv.length > 4 || !/^\d+$/.test(cardCvv)) {
        isValid = false;
        errorMessage = 'Введите корректный CVV код (3-4 цифры)';
        highlightField('card-cvv', false);
    } else {
        highlightField('card-cvv', true);
    }

    if (!cardHolder || cardHolder.length < 2 || !/^[a-zA-Zа-яА-Я\s]{2,}$/.test(cardHolder)) {
        isValid = false;
        errorMessage = 'Введите имя и фамилию владельца карты';
        highlightField('card-holder', false);
    } else {
        highlightField('card-holder', true);
    }

    if (!isValid) {
        showMessage(errorMessage);
        return false;
    }

    return true;
}

function highlightField(fieldId, isValid) {
    const field = document.getElementById(fieldId);
    if (field) {
        if (isValid) {
            field.style.borderColor = '#10b981';
            field.style.backgroundColor = '#f0fdf4';
        } else {
            field.style.borderColor = '#ef4444';
            field.style.backgroundColor = '#fef2f2';
        }
    }
}

function resetPaymentForm() {
    const fields = ['card-number', 'card-expiry', 'card-cvv', 'card-holder'];
    fields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            field.value = '';
            field.style.borderColor = '';
            field.style.backgroundColor = '';
        }
    });
}


async function reserveTickets(museumCode, date, startTime, quantity) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/time-slots/reserve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                museum_code: museumCode,
                date: date,
                start_time: startTime,
                quantity: quantity
            })
        });
        
        if (response.ok) {
            return await response.json();
        } else {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Не удалось забронировать билеты');
        }
    } catch (error) {
        console.error('Ошибка при бронировании:', error);
        throw error;
    }
}

let dateSlotsContainer = document.getElementById('date-slots-container');

async function generateDateSlots() {
    if (!currentMuseumId) return;
    
    if (!dateSlotsContainer) return;
    
    if (dateSlotsContainer.children.length === 0) {
        dateSlotsContainer.innerHTML = `
            <div class="loading-slots">
                <div class="loading-spinner"></div>
                <p>Загрузка слотов...</p>
            </div>
        `;
    }
    
    const today = new Date();
    
    try {
        const slotsPromises = [];
        for (let i = 0; i < 14; i++) {
            const date = new Date();
            date.setDate(today.getDate() + i);
            const dateString = date.toISOString().split('T')[0];
            
            slotsPromises.push(getAvailableTimeSlots(currentMuseumId, dateString));
        }
        
        const allSlots = await Promise.all(slotsPromises);
        
        if (dateSlotsContainer.querySelector('.loading-slots')) {
            dateSlotsContainer.innerHTML = '';
        }
        
        if (dateSlotsContainer.children.length > 0) {
            updateExistingSlots(dateSlotsContainer, allSlots, today);
        } else {
            fillSlotsContainer(dateSlotsContainer, allSlots, today);
        }
        
        restoreSelectedSlot();
        
        addTimeSlotListeners();
        
    } catch (error) {
        console.error('Ошибка при загрузке слотов:', error);
        if (dateSlotsContainer.children.length === 0 || dateSlotsContainer.querySelector('.loading-slots')) {
            dateSlotsContainer.innerHTML = `
                <div class="error-slots">
                    <p>Ошибка загрузки слотов</p>
                    <button onclick="generateDateSlots()" class="retry-button">Попробовать снова</button>
                </div>
            `;
        }
    }
}


function updateExistingSlots(container, allSlots, today) {
    for (let i = 0; i < 14; i++) {
        const date = new Date();
        date.setDate(today.getDate() + i);
        const dateString = date.toISOString().split('T')[0];
        const daySlots = allSlots[i] || [];
        
        const dateElement = container.children[i];
        if (!dateElement) continue;
        
        const timeSlotsContainer = dateElement.querySelector('.time-slots');
        if (!timeSlotsContainer) continue;
        
        const existingTimeSlots = timeSlotsContainer.querySelectorAll('.time-slot');
        
        daySlots.forEach((slot, slotIndex) => {
            if (existingTimeSlots[slotIndex]) {
                updateSingleTimeSlot(existingTimeSlots[slotIndex], slot, dateString);
            }
        });
    }
}

function updateSingleTimeSlot(timeSlotElement, slotData, dateString) {
    const availableTickets = slotData.available_tickets;
    const isAvailable = availableTickets > 0;
    
    timeSlotElement.setAttribute('data-available', availableTickets);
    
    const ticketsElement = timeSlotElement.querySelector('.tickets-available');
    if (ticketsElement) {
        ticketsElement.textContent = isAvailable ? `${availableTickets} билетов` : 'Распродано';
    }
    
    if (isAvailable) {
        timeSlotElement.classList.remove('sold-out');
        timeSlotElement.classList.add('available');
    } else {
        timeSlotElement.classList.add('sold-out');
        timeSlotElement.classList.remove('available');
    }
    
    if (timeSlotElement.classList.contains('selected') && !isAvailable) {
        timeSlotElement.classList.remove('selected');
        selectedDateSlot = null;
        selectedTimeSlot = null;
        currentAvailableTickets = 0;
        updateDateSelection();
        showMessage('Выбранный слот больше не доступен. Пожалуйста, выберите другой.');
    }
    
    if (timeSlotElement.classList.contains('selected') && isAvailable) {
        const selectedCount = parseInt(document.getElementById('tickets').value);
        
        if (selectedCount > availableTickets) {
            showMessage(`В выбранном слоте теперь доступно только ${availableTickets} билетов. Количество билетов уменьшено.`);
            document.getElementById('tickets').value = availableTickets;
            
            ticketCategories = ticketCategories.slice(0, availableTickets);
            
            updateTicketCategoriesUI();
            updateTotal();
        }
        
        currentAvailableTickets = availableTickets;
    }
}

function fillSlotsContainer(container, allSlots, today) {
    container.innerHTML = '';
    
    for (let i = 0; i < 14; i++) {
        const date = new Date();
        date.setDate(today.getDate() + i);
        const dateString = date.toISOString().split('T')[0];
        const daySlots = allSlots[i] || [];
        
        const dateElement = document.createElement('div');
        dateElement.className = 'date-slot';
        
        const dateStringFormatted = date.toLocaleDateString('ru-RU', { 
            weekday: 'short',
            day: 'numeric', 
            month: 'long' 
        });
        
        dateElement.innerHTML = `
            <div class="date-text">${dateStringFormatted}</div>
            <div class="time-slots">
                ${generateTimeSlotsHTML(daySlots, dateString)}
            </div>
        `;
        
        container.appendChild(dateElement);
    }
}

function restoreSelectedSlot() {
    if (selectedDateSlot && selectedTimeSlot) {
        const selectedSlot = document.querySelector(
            `.time-slot[data-date="${selectedDateSlot}"][data-time="${selectedTimeSlot}"]`
        );
        
        if (selectedSlot && selectedSlot.classList.contains('available')) {
            const available = parseInt(selectedSlot.getAttribute('data-available'));
            currentAvailableTickets = available;
            
            const ticketCount = parseInt(document.getElementById('tickets').value);
            if (ticketCount > available) {
                document.getElementById('tickets').value = available;
                updateTotal();
                showMessage(`В выбранном слоте теперь доступно только ${available} билетов`);
            }
            
            document.querySelectorAll('.time-slot').forEach(s => {
                s.classList.remove('selected');
            });
            selectedSlot.classList.add('selected');
        } else {
            selectedDateSlot = null;
            selectedTimeSlot = null;
            currentAvailableTickets = 0;
            updateDateSelection();
        }
    }
}


function generateTimeSlotsHTML(daySlots, dateString) {
    if (!daySlots || daySlots.length === 0) {
        return '<div class="no-slots">Нет доступных слотов</div>';
    }
    
    return daySlots.map(slot => {
        const availableTickets = slot.available_tickets;
        const isAvailable = availableTickets > 0;
        const timeDisplay = formatTimeDisplay(slot.start_time, slot.end_time);
        
        const classes = [
            'time-slot',
            isAvailable ? 'available' : 'sold-out',
            selectedDateSlot === dateString && selectedTimeSlot === slot.start_time ? 'selected' : ''
        ].filter(Boolean).join(' ');
        
        return `
            <div class="${classes}" 
                 data-date="${dateString}" 
                 data-time="${slot.start_time}"
                 data-available="${availableTickets}">
                <div class="time-text">${timeDisplay}</div>
                <div class="tickets-available">
                    ${isAvailable ? `${availableTickets} билетов` : 'Распродано'}
                </div>
            </div>
        `;
    }).join('');
}

function formatTimeDisplay(startTime, endTime) {
    const start = startTime.substring(0, 5);
    const end = endTime.substring(0, 5);
    return `${start}-${end}`;
}

function addTimeSlotListeners() {
    document.querySelectorAll('.time-slot.available').forEach(slot => {
        slot.replaceWith(slot.cloneNode(true));
    });
    
    document.querySelectorAll('.time-slot.available').forEach(slot => {
        slot.addEventListener('click', function() {
            handleTimeSlotSelection(this);
        });
    });
}

function handleTimeSlotSelection(slotElement) {
    const available = parseInt(slotElement.getAttribute('data-available'));
    currentAvailableTickets = available;
    
    const selectedCount = parseInt(document.getElementById('tickets').value);
    
    if (selectedCount > available) {
        showMessage(`В выбранном слоте доступно только ${available} билетов. Количество билетов уменьшено до ${available}.`);
        
        document.getElementById('tickets').value = available;
        
        ticketCategories = ticketCategories.slice(0, available);
        
        updateTicketCategoriesUI();
        updateTotal();
    }
    
    document.querySelectorAll('.time-slot').forEach(s => {
        s.classList.remove('selected');
    });
    
    slotElement.classList.add('selected');
    
    selectedDateSlot = slotElement.getAttribute('data-date');
    selectedTimeSlot = slotElement.getAttribute('data-time');
    
    updateDateSelection();
    
    console.log('Выбран слот:', selectedDateSlot, selectedTimeSlot, 'Доступно билетов:', available);
}

function updateDateSelection() {
    const dateButton = document.querySelector('.date-button');
    if (!dateButton) return;
    
    if (selectedDateSlot && selectedTimeSlot) {
        const date = new Date(selectedDateSlot);
        const dateString = date.toLocaleDateString('ru-RU', { 
            weekday: 'long',
            day: 'numeric', 
            month: 'long' 
        });
        
        const timeDisplay = getTimeDisplay(selectedTimeSlot);
        
        dateButton.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-calendar mr-2">
                <path d="M8 2v4"></path>
                <path d="M16 2v4"></path>
                <rect width="18" height="18" x="3" y="4" rx="2"></rect>
                <path d="M3 10h18"></path>
            </svg>
            ${dateString}, ${timeDisplay}
        `;
    } else {
        dateButton.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-calendar mr-2">
                <path d="M8 2v4"></path>
                <path d="M16 2v4"></path>
                <rect width="18" height="18" x="3" y="4" rx="2"></rect>
                <path d="M3 10h18"></path>
            </svg>
            Выберите дату и время
        `;
    }
}

function getTimeDisplay(startTime) {
    const timeMap = {
        '10:00:00': '10:00-12:00',
        '12:00:00': '12:00-14:00', 
        '14:00:00': '14:00-16:00',
        '16:00:00': '16:00-18:00'
    };
    return timeMap[startTime] || startTime;
}

function scrollDates(direction) {
    const container = document.getElementById('date-slots-container');
    if (container) {
        const scrollAmount = 432;
        container.scrollLeft += direction * scrollAmount;
    }
}

function showPaymentModal() {
    resetPaymentForm();
    
    const totalPrice = document.getElementById('total-price').textContent;
    const totalPricePayment = document.getElementById('total-price-payment');
    if (totalPricePayment) {
        totalPricePayment.textContent = totalPrice;
    }
    
    document.getElementById('payment-modal').style.display = 'flex';
    
    const payButton = document.querySelector('#payment-modal .modal-content button.payment-button.primary');
    if (payButton) {
        payButton.innerHTML = 'Оплатить ' + totalPrice;
        payButton.disabled = false;
    }
}

function closePaymentModal() {
    document.getElementById('payment-modal').style.display = 'none';
    cancelReservation();
}

async function processPayment() {
    if (!validatePaymentForm()) {
        return;
    }

    const ticketCount = parseInt(document.getElementById('tickets').value);
    
    try {
        const payButton = document.querySelector('#payment-modal .modal-content button.payment-button.primary');
        const originalText = payButton.textContent;
        payButton.innerHTML = '<div class="loading-spinner"></div> Обработка оплаты...';
        payButton.disabled = true;

        const finalResponse = await fetch(`${API_BASE_URL}/api/time-slots/confirm-payment`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                museum_code: currentMuseumId,
                date: selectedDateSlot,
                start_time: selectedTimeSlot,
                quantity: ticketCount,
                visitor_id: currentUser.id
            })
        });
        
        if (finalResponse.ok) {
            const result = await finalResponse.json();
            
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            closePaymentModal();
            showMessage('✅ Оплата прошла успешно! Билеты забронированы.');
            
            await generateTicket();
            
            resetPaymentForm();
            
            window.currentReservation = null;
            
        } else {
            const errorData = await finalResponse.json();
            throw new Error(errorData.detail || 'Ошибка подтверждения оплаты');
        }
        
    } catch (error) {
        console.error('Ошибка при обработке оплаты:', error);
        showMessage(error.message || 'Ошибка при обработке оплаты. Пожалуйста, попробуйте еще раз.');
        
        const payButton = document.querySelector('#payment-modal .modal-content button.payment-button.primary');
        payButton.innerHTML = 'Оплатить ' + document.getElementById('total-price').textContent;
        payButton.disabled = false;
    }
}

async function buyTickets() {
    if (!currentUser) {
        showMessage('Для покупки билетов необходимо зарегистрироваться');
        showAuthModal();
        return;
    }
    
    if (!selectedDateSlot || !selectedTimeSlot) {
        showMessage('Пожалуйста, выберите дату и время посещения');
        
        const dateButton = document.querySelector('.date-button');
        if (dateButton) {
            dateButton.style.border = '2px solid #ef4444';
            dateButton.style.backgroundColor = '#fef2f2';
            setTimeout(() => {
                dateButton.style.border = '';
                dateButton.style.backgroundColor = '';
            }, 2000);
        }
        return;
    }
    
    const ticketCount = parseInt(document.getElementById('tickets').value);
    
    if (ticketCount > currentAvailableTickets) {
        showMessage(`В выбранном слоте доступно только ${currentAvailableTickets} билетов. Уменьшите количество билетов.`);
        return;
    }
    
    if (ticketCount > 10) {
        showMessage('Нельзя заказать больше 10 билетов за один раз');
        return;
    }
    
    showPaymentModal();
    
    reserveTicketsInBackground(currentMuseumId, selectedDateSlot, selectedTimeSlot, ticketCount);
}

async function reserveTicketsInBackground(museumCode, date, startTime, quantity) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/time-slots/reserve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                museum_code: museumCode,
                date: date,
                start_time: startTime,
                quantity: quantity
            })
        });
        
        if (response.ok) {
            console.log('✅ Билеты временно забронированы');
            window.currentReservation = {
                museumCode: museumCode,
                date: date,
                startTime: startTime,
                quantity: quantity
            };
        } else {
            console.error('❌ Ошибка бронирования');
        }
    } catch (error) {
        console.error('Ошибка сети при бронировании:', error);
    }
}

async function cancelReservation() {
    if (!window.currentReservation) return;
    
    try {
        console.log('Отмена бронирования');
        generateDateSlots();
    } catch (error) {
        console.error('Ошибка при отмене бронирования:', error);
    } finally {
        window.currentReservation = null;
    }
}

function generateTicket() {
    if (!currentMuseumId) {
        showMessage('Ошибка: не выбран музей');
        return;
    }
    
    const museum = museumData[currentMuseumId];
    const ticketCount = parseInt(document.getElementById('tickets').value);
    
    let totalPrice = 0;
    const baseTicketNumber = 'T' + Date.now();
    const individualTickets = ticketCategories.map((category, index) => {
        const multiplier = multipliers[category] || 1.0;
        const price = Math.round(currentMuseumPrice * multiplier);
        totalPrice += price;
        
        return {
            category: category,
            price: price,
            ticketNumber: baseTicketNumber + '-' + (index + 1).toString().padStart(2, '0')
        };
    });

    window.newTicketNumbers = [baseTicketNumber];
    
    saveTicketToDatabase(museum, baseTicketNumber, ticketCount, totalPrice);
    
    setTimeout(() => {
        closeMuseumDetail();
        showMyTickets(window.newTicketNumbers);
    }, 500);
    
    return true;
}

function saveTicket() {
    const ticketElement = document.getElementById('ticket-container');
    
    if (typeof html2canvas === 'undefined') {
        showMessage('Билет сохранен в базе данных');
        return;
    }
    
    html2canvas(ticketElement).then(canvas => {
        canvas.toBlob(function(blob) {
            const link = document.createElement('a');
            link.download = 'билет.png';
            link.href = URL.createObjectURL(blob);
            link.click();
            URL.revokeObjectURL(link.href);
            showMessage('Билет сохранен как изображение');
        });
    }).catch(error => {
        console.error('Ошибка при создании изображения:', error);
        showMessage('Билет сохранен в базе данных');
    });
}

function shareTicket() {
    if (!currentMuseumId) {
        showMessage('Ошибка: информация о музее не найдена');
        return;
    }
    
    const museum = museumData[currentMuseumId];
    
    if (navigator.share) {
        navigator.share({
            title: 'Мой билет в музей',
            text: `Билет в ${museum.title}`,
            url: window.location.href
        }).catch(error => {
            console.log('Ошибка при попытке поделиться:', error);
        });
    } else {
        showMessage('Функция "Поделиться" не поддерживается в вашем браузере');
    }
}

let ticketsRefreshInterval = null;

function showMyTickets(newTicketNumbers = []) {
    if (!currentUser) {
        showMessage('Для просмотра билетов необходимо войти в систему');
        showAuthModal();
        return;
    }
    
    document.getElementById('museum-detail').style.display = 'none';
    
    document.getElementById('my-tickets-section').style.display = 'block';
    document.body.style.overflow = 'hidden';
    
    window.newTicketNumbers = newTicketNumbers;
    
    loadUserTickets();
    
    startTicketsAutoRefresh();
    
    console.log('✅ Переход в раздел "Мои билеты" выполнен');
}

function closeMyTickets() {
    document.getElementById('my-tickets-section').style.display = 'none';
    document.body.style.overflow = 'auto';
    
    stopTicketsAutoRefresh();
}

function startTicketsAutoRefresh() {
    stopTicketsAutoRefresh();
    
    ticketsRefreshInterval = setInterval(() => {
        if (document.getElementById('my-tickets-section').style.display === 'block') {
            console.log('🔄 Автоматическое обновление списка билетов...');
            loadUserTickets();
        }
    }, 3000);
}

function stopTicketsAutoRefresh() {
    if (ticketsRefreshInterval) {
        clearInterval(ticketsRefreshInterval);
        ticketsRefreshInterval = null;
    }
}

async function loadUserTickets() {
    if (!currentUser) return;
    
    try {
        console.log('Загружаем билеты для пользователя ID:', currentUser.id);
        
        const response = await fetch(`${API_BASE_URL}/api/tickets/${currentUser.id}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            mode: 'cors'
        });
        
        console.log('Статус ответа:', response.status);
        
        if (response.ok) {
            const tickets = await response.json();
            console.log('Получены все билеты:', tickets);
            
            const uncheckedTickets = tickets.filter(ticket => {
                const checkValue = ticket.check;
                console.log(`Билет ${ticket.ticket_number}: check =`, checkValue);
                
                return !checkValue || 
                       checkValue === '' || 
                       checkValue.toString().toLowerCase().trim() !== 'проверено';
            });
            
            console.log('Непроверенные билеты после фильтрации:', uncheckedTickets);
            displayTickets(uncheckedTickets);
        } else {
            console.error('Ошибка при загрузке билетов, статус:', response.status);
            
            let errorText = 'Неизвестная ошибка сервера';
            try {
                errorText = await response.text();
            } catch (e) {
                console.error('Не удалось получить текст ошибки:', e);
            }
            
            console.error('Текст ошибки:', errorText);
            showMessage('Ошибка при загрузке билетов: ' + errorText);
            displayTickets([]);
        }
    } catch (error) {
        console.error('Ошибка сети при загрузке билетов:', error);
        
        if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
            showMessage('Ошибка подключения к серверу. Проверьте: 1) Сервер запущен 2) CORS настроен 3) Сетевые настройки');
        } else {
            showMessage('Ошибка сети: ' + error.message);
        }
        
        displayTickets([]);
    }
}


function generateBarcodeDataURL(text, width = 200, height = 80) {
    return new Promise((resolve) => {
        try {
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            
            ctx.fillStyle = '#FFFFFF';
            ctx.fillRect(0, 0, width, height);
            
            const binarySequence = textToBinary(text);
            
            drawBarcode(ctx, binarySequence, width, height);
            
            resolve(canvas.toDataURL('image/png', 1.0));
        } catch (error) {
            console.error('Ошибка при создании штрих-кода:', error);
            resolve(createSimpleBarcode(text, width, height));
        }
    });
}

function textToBinary(text) {
    let binary = '';
    for (let i = 0; i < text.length; i++) {
        const charCode = text.charCodeAt(i);
        const binaryChar = (charCode & 0x0F).toString(2).padStart(4, '0');
        binary += binaryChar;
    }
    return binary;
}

function drawBarcode(ctx, binarySequence, width, height) {
    const barWidth = Math.max(1, Math.floor(width / binarySequence.length));
    const actualWidth = barWidth * binarySequence.length;
    const startX = (width - actualWidth) / 2;
    
    ctx.fillStyle = '#000000';
    
    for (let i = 0; i < binarySequence.length; i++) {
        if (binarySequence[i] === '1') {
            const x = startX + i * barWidth;
            ctx.fillRect(x, 0, barWidth, height);
        }
    }
    
    ctx.fillStyle = '#000000';
    ctx.font = 'bold 12px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillText('ШТРИХ-КОД', width / 2, height + 5);
}

function createSimpleBarcode(text, width = 200, height = 80) {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height + 20;
    const ctx = canvas.getContext('2d');
    
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, width, height + 20);
    
    ctx.fillStyle = '#000000';
    const barCount = 30;
    const barWidth = width / barCount;
    
    for (let i = 0; i < barCount; i++) {
        const charCode = text.charCodeAt(i % text.length);
        if (charCode % 3 !== 0) {
            const x = i * barWidth;
            const barHeight = height - (i % 3) * 10;
            ctx.fillRect(x, 0, barWidth, barHeight);
        }
    }
    
    ctx.fillStyle = '#000000';
    ctx.font = 'bold 10px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    
    if (text.length > 20) {
        const firstPart = text.substring(0, 20);
        const secondPart = text.substring(20, 40);
        ctx.fillText(firstPart, width / 2, height + 5);
        ctx.fillText(secondPart, width / 2, height + 18);
    } else {
        ctx.fillText(text, width / 2, height + 5);
    }
    
    return canvas.toDataURL('image/png', 1.0);
}

function createFallbackQRCode(text, size = 120) {
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, size, size);
    
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 3;
    ctx.strokeRect(5, 5, size - 10, size - 10);
    
    ctx.fillStyle = '#000000';
    
    const cellSize = 8;
    const cols = Math.floor((size - 20) / cellSize);
    const rows = Math.floor((size - 20) / cellSize);
    
    for (let i = 0; i < cols; i++) {
        for (let j = 0; j < rows; j++) {
            if (Math.random() > 0.6) {
                const x = 10 + i * cellSize;
                const y = 10 + j * cellSize;
                ctx.fillRect(x, y, cellSize - 1, cellSize - 1);
            }
        }
    }
    
    ctx.fillRect(10, 10, 20, 20);
    ctx.clearRect(15, 15, 10, 10);
    
    ctx.fillRect(size - 30, 10, 20, 20);
    ctx.clearRect(size - 25, 15, 10, 10);
    
    ctx.fillRect(10, size - 30, 20, 20);
    ctx.clearRect(15, size - 25, 10, 10);
    
    ctx.fillStyle = '#000000';
    ctx.font = 'bold 10px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    
    if (text.length > 12) {
        const firstPart = text.substring(0, 12);
        const secondPart = text.substring(12, 24);
        ctx.fillText(firstPart, size/2, size/2 - 8);
        ctx.fillText(secondPart, size/2, size/2 + 8);
    } else {
        ctx.fillText(text, size/2, size/2);
    }
    
    return canvas.toDataURL('image/png');
}

function createSimpleQRCode(text, size = 120) {
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, size, size);
    
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 3;
    ctx.strokeRect(5, 5, size - 10, size - 10);
    
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 1;
    
    for (let i = 15; i < size; i += 15) {
        ctx.beginPath();
        ctx.moveTo(i, 10);
        ctx.lineTo(i, size - 10);
        ctx.stroke();
    }
    
    for (let i = 15; i < size; i += 15) {
        ctx.beginPath();
        ctx.moveTo(10, i);
        ctx.lineTo(size - 10, i);
        ctx.stroke();
    }
    
    ctx.fillStyle = '#000000';
    ctx.font = 'bold 10px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    
    if (text.length > 15) {
        const firstPart = text.substring(0, 15);
        const secondPart = text.substring(15);
        ctx.fillText(firstPart, size/2, size/2 - 10);
        ctx.fillText(secondPart, size/2, size/2 + 10);
    } else {
        ctx.fillText(text, size/2, size/2);
    }
    
    return canvas.toDataURL('image/png', 1.0);
}

function createSimpleQRCode(text, size = 120) {
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, size, size);
    
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 3;
    ctx.strokeRect(5, 5, size - 10, size - 10);
    
    ctx.fillStyle = '#000000';
    ctx.font = 'bold 14px Arial';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('БИЛЕТ', size/2, size/2 - 10);
    
    ctx.font = 'bold 10px Arial';
    ctx.fillText(text.substring(0, 15), size/2, size/2 + 10);
    
    return canvas.toDataURL('image/png', 1.0);
}

async function displayTickets(tickets) {
    const ticketsGrid = document.getElementById('tickets-grid');
    const noTicketsMessage = document.getElementById('no-tickets-message');
    
    if (!ticketsGrid || !noTicketsMessage) {
        console.error('Не найдены элементы для отображения билетов');
        return;
    }
    
    console.log('Отображаем билеты, количество:', tickets.length);
    
    if (!tickets || tickets.length === 0) {
        ticketsGrid.innerHTML = '';
        noTicketsMessage.style.display = 'block';
        noTicketsMessage.innerHTML = `
            <div style="text-align: center; padding: 2rem;">
                <h3>Нет активных билетов</h3>
                <p style="color: var(--text-light); margin-top: 0.5rem;">
                    ${currentUser ? 'У вас нет непроверенных билетов. Проверенные билеты автоматически скрываются.' : 'Войдите в систему для просмотра билетов'}
                </p>
            </div>
        `;
        return;
    }
    
    noTicketsMessage.style.display = 'none';
    
    const ticketsWithQR = await Promise.all(
        tickets.map(async (ticket) => {
            try {
                const qrCodeDataURL = await generateQRCodeDataURL(ticket.ticket_number, 120);
                return { ...ticket, qrCodeDataURL };
            } catch (error) {
                console.error('Ошибка при генерации QR-кода для билета', ticket.ticket_number, error);
                const fallbackQR = createSimpleQRCode(ticket.ticket_number, 120);
                return { ...ticket, qrCodeDataURL: fallbackQR };
            }
        })
    );
    
    const ticketsHTML = ticketsWithQR.map(ticket => {
        const isNewTicket = window.newTicketNumbers && 
                           window.newTicketNumbers.some(newNumber => 
                               ticket.ticket_number && 
                               ticket.ticket_number.includes(newNumber.replace('T', '').split('-')[0])
                           );
        
        const museumName = ticket.museum_name || ticket.museum_code || 'Неизвестный музей';
        const visitorName = ticket.visitor_name || currentUser?.name || 'Не указано';
        const visitorSurname = ticket.visitor_surname || currentUser?.surname || '';
        const visitorPhone = ticket.visitor_phone || currentUser?.phone || 'Не указан';
        const ticketType = ticket.ticket_type || 'Стандартный';
        const price = ticket.price || 0;
        const visitDate = ticket.visit_date ? formatDate(ticket.visit_date) : 'Не указана';
        const visitTime = ticket.visit_time ? formatTime(ticket.visit_time) : '';
        
        const purchaseDate = ticket.issued_at ? formatDateTime(ticket.issued_at) : 
                            (ticket.created_at ? formatDateTime(ticket.created_at) : 
                            (ticket.purchase_date ? formatDateTime(ticket.purchase_date) : 'Не указана'));
        
        return `
        <div class="ticket-card-compact ${isNewTicket ? 'new-ticket' : ''}">
            ${isNewTicket ? '<div class="new-ticket-badge">НОВЫЙ</div>' : ''}
            <div class="ticket-status-indicator" style="background: #10b981;"></div>
            <div class="ticket-header-compact">
                <h3>${museumName}</h3>
                <div class="ticket-category-badge">${ticketType}</div>
            </div>
            
            <div class="ticket-body-compact">
                <div class="ticket-info-compact">
                    <div class="info-row-compact">
                        <span class="info-label-compact">Посетитель:</span>
                        <span class="info-value-compact">${visitorName} ${visitorSurname}</span>
                    </div>
                    <div class="info-row-compact">
                        <span class="info-label-compact">Телефон:</span>
                        <span class="info-value-compact">${visitorPhone}</span>
                    </div>
                    <div class="info-row-compact">
                        <span class="info-label-compact">Приобретено:</span>
                        <span class="info-value-compact" style="color: #10b981; font-weight: bold;">${purchaseDate}</span>
                    </div>
                    <div class="info-row-compact">
                        <span class="info-label-compact">Дата посещения:</span>
                        <span class="info-value-compact">${visitDate} ${visitTime}</span>
                    </div>
                    <div class="info-row-compact">
                        <span class="info-label-compact">Сумма:</span>
                        <span class="info-value-compact" style="font-weight: bold; color: #3b82f6;">${price}₽</span>
                    </div>
                </div>
                
                <div class="ticket-number-compact">
                    № ${ticket.ticket_number}
                </div>
                
                <div class="qr-code-compact">
                    <p style="font-size: 0.8rem; margin-bottom: 0.5rem; color: #666; text-align: center;">QR-код для входа</p>
                    <img src="${ticket.qrCodeDataURL}" alt="QR Code" 
                         style="width: 120px; height: 120px; border: 2px solid #000; border-radius: 8px; background: white; display: block; margin: 0 auto;">
                </div>
                
                <div class="ticket-actions-compact">
                    <button class="action-btn-compact save-btn-compact" onclick="saveSingleTicket(this)">
                        Сохранить
                    </button>
                    <button class="action-btn-compact share-btn-compact" onclick="shareSingleTicket('${ticket.ticket_number}')">
                        Поделиться
                    </button>
                </div>
            </div>
        </div>
    `}).join('');
    
    ticketsGrid.innerHTML = ticketsHTML;
    
    if (window.newTicketNumbers && window.newTicketNumbers.length > 0) {
        setTimeout(() => {
            const newTickets = document.querySelectorAll('.ticket-card-compact.new-ticket');
            newTickets.forEach(ticket => {
                ticket.classList.remove('new-ticket');
                const badge = ticket.querySelector('.new-ticket-badge');
                if (badge) badge.remove();
            });
            window.newTicketNumbers = [];
            console.log('Подсветка новых билетов убрана');
        }, 7000);
    }
}

function saveSingleTicket(button) {
    const ticketCard = button.closest('.ticket-card-compact');
    if (typeof html2canvas === 'undefined') {
        showMessage('Функция сохранения недоступна');
        return;
    }

    const originalText = button.textContent;
    button.textContent = 'Сохраняем...';
    button.disabled = true;

    const tempContainer = document.createElement('div');
    tempContainer.style.position = 'fixed';
    tempContainer.style.left = '0';
    tempContainer.style.top = '0';
    tempContainer.style.width = '400px';
    tempContainer.style.zIndex = '10000';
    tempContainer.style.opacity = '0';
    tempContainer.style.pointerEvents = 'none';
    
    const clone = ticketCard.cloneNode(true);
    clone.style.width = '380px';
    clone.style.margin = '0 auto';
    clone.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.1)';
    clone.style.transform = 'scale(1)';
    
    tempContainer.appendChild(clone);
    document.body.appendChild(tempContainer);

    setTimeout(() => {
        const images = clone.getElementsByTagName('img');
        let imagesLoaded = 0;
        const totalImages = images.length;

        if (totalImages === 0) {
            captureTicket();
            return;
        }

        const imageLoadPromises = Array.from(images).map(img => {
            return new Promise((resolve) => {
                if (img.complete) {
                    resolve();
                } else {
                    img.onload = resolve;
                    img.onerror = resolve;
                    setTimeout(resolve, 1000);
                }
            });
        });

        Promise.all(imageLoadPromises).then(() => {
            setTimeout(captureTicket, 100);
        });

        function captureTicket() {
            html2canvas(clone, {
                scale: 2,
                useCORS: true,
                logging: false,
                backgroundColor: '#ffffff',
                allowTaint: false,
                width: clone.offsetWidth,
                height: clone.offsetHeight,
                scrollX: 0,
                scrollY: 0,
                onclone: function(clonedDoc, element) {
                    element.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.15)';
                    element.style.borderRadius = '16px';
                    
                    const textElements = element.querySelectorAll('*');
                    textElements.forEach(el => {
                        const computedStyle = window.getComputedStyle(el);
                        if (computedStyle.color === 'rgba(0, 0, 0, 0)' || computedStyle.color === 'transparent') {
                            el.style.color = '#000000';
                        }
                    });
                    
                    const qrImages = element.querySelectorAll('.qr-code-compact img');
                    qrImages.forEach(img => {
                        img.style.display = 'block';
                        img.style.visibility = 'visible';
                        img.style.opacity = '1';
                    });
                }
            }).then(canvas => {
                const finalCanvas = document.createElement('canvas');
                finalCanvas.width = canvas.width;
                finalCanvas.height = canvas.height;
                const ctx = finalCanvas.getContext('2d');
                
                ctx.fillStyle = '#FFFFFF';
                ctx.fillRect(0, 0, finalCanvas.width, finalCanvas.height);
                
                ctx.drawImage(canvas, 0, 0);
                
                const link = document.createElement('a');
                const ticketNumber = ticketCard.querySelector('.ticket-number-compact')?.textContent?.replace(/[^\w]/g, '') || 'ticket';
                link.download = `билет_${ticketNumber}.png`;
                link.href = finalCanvas.toDataURL('image/png', 1.0);
                
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                
                document.body.removeChild(tempContainer);
                
                button.textContent = '✓ Сохранено';
                button.style.background = '#10b981';
                setTimeout(() => {
                    button.textContent = originalText;
                    button.style.background = '';
                    button.disabled = false;
                }, 2000);
                
                showMessage('Билет успешно сохранен!');
                
            }).catch(error => {
                console.error('Ошибка при создании изображения:', error);
                document.body.removeChild(tempContainer);
                fallbackSaveTicket(ticketCard, button, originalText);
            });
        }
    }, 500);
}

function fallbackSaveTicket(ticketCard, button, originalText) {
    const ticketInfo = {
        number: ticketCard.querySelector('.ticket-number-compact')?.textContent || 'Неизвестно',
        museum: ticketCard.querySelector('h3')?.textContent || 'Неизвестный музей',
        visitor: ticketCard.querySelector('.info-value-compact')?.textContent || 'Неизвестно',
        date: Array.from(ticketCard.querySelectorAll('.info-value-compact'))[3]?.textContent || 'Неизвестно'
    };
    
    const textContent = `
БИЛЕТ В МУЗЕЙ
===============
Номер: ${ticketInfo.number}
Музей: ${ticketInfo.museum}
Посетитель: ${ticketInfo.visitor}
Дата посещения: ${ticketInfo.date}

Сохраните этот QR-код для входа в музей.
QR-код будет доступен в мобильном приложении.
    `.trim();
    
    const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
    const link = document.createElement('a');
    link.download = `билет_${ticketInfo.number.replace(/\s+/g, '_')}.txt`;
    link.href = URL.createObjectURL(blob);
    link.click();
    URL.revokeObjectURL(link.href);
    
    button.textContent = originalText;
    button.disabled = false;
    showMessage('Билет сохранен в текстовом формате');
}

function createFallbackQRCode(text, size) {
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, size, size);
    
    ctx.strokeStyle = '#000000';
    ctx.lineWidth = 2;
    ctx.strokeRect(5, 5, size - 10, size - 10);
    
    ctx.fillStyle = '#000000';
    ctx.font = 'bold 14px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('QR CODE', size/2, size/2 - 10);
    ctx.font = '10px Arial';
    ctx.fillText(text.substring(0, 15), size/2, size/2 + 10);
    
    return canvas.toDataURL();
}

async function displayTickets(tickets) {
    const ticketsGrid = document.getElementById('tickets-grid');
    const noTicketsMessage = document.getElementById('no-tickets-message');
    
    if (!ticketsGrid || !noTicketsMessage) {
        console.error('Не найдены элементы для отображения билетов');
        return;
    }
    
    console.log('Отображаем билеты, количество:', tickets.length);
    
    if (!tickets || tickets.length === 0) {
        ticketsGrid.innerHTML = '';
        noTicketsMessage.style.display = 'block';
        noTicketsMessage.innerHTML = `
            <div style="text-align: center; padding: 2rem;">
                <h3>Нет активных билетов</h3>
                <p style="color: var(--text-light); margin-top: 0.5rem;">
                    ${currentUser ? 'У вас нет непроверенных билетов. Проверенные билеты автоматически скрываются.' : 'Войдите в систему для просмотра билетов'}
                </p>
            </div>
        `;
        return;
    }
    
    noTicketsMessage.style.display = 'none';
    
    const ticketsWithBarcode = await Promise.all(
        tickets.map(async (ticket) => {
            try {
                const barcodeDataURL = await generateBarcodeDataURL(ticket.ticket_number, 200, 60);
                return { ...ticket, barcodeDataURL };
            } catch (error) {
                console.error('Ошибка при генерации штрих-кода для билета', ticket.ticket_number, error);
                const fallbackBarcode = createSimpleBarcode(ticket.ticket_number, 200, 60);
                return { ...ticket, barcodeDataURL: fallbackBarcode };
            }
        })
    );
    
    const ticketsHTML = ticketsWithBarcode.map(ticket => {
        const isNewTicket = window.newTicketNumbers && 
                           window.newTicketNumbers.some(newNumber => 
                               ticket.ticket_number && 
                               ticket.ticket_number.includes(newNumber.replace('T', '').split('-')[0])
                           );
        
        const museumName = ticket.museum_name || ticket.museum_code || 'Неизвестный музей';
        const visitorName = ticket.visitor_name || currentUser?.name || 'Не указано';
        const visitorSurname = ticket.visitor_surname || currentUser?.surname || '';
        const visitorPhone = ticket.visitor_phone || currentUser?.phone || 'Не указан';
        const ticketType = ticket.ticket_type || 'Стандартный';
        const price = ticket.price || 0;
        const visitDate = ticket.visit_date ? formatDate(ticket.visit_date) : 'Не указана';
        const visitTime = ticket.visit_time ? formatTime(ticket.visit_time) : '';
        
        const purchaseDate = ticket.issued_at ? formatDateTime(ticket.issued_at) : 
                            (ticket.created_at ? formatDateTime(ticket.created_at) : 
                            (ticket.purchase_date ? formatDateTime(ticket.purchase_date) : 'Не указана'));
        
        return `
        <div class="ticket-card-compact ${isNewTicket ? 'new-ticket' : ''}">
            ${isNewTicket ? '<div class="new-ticket-badge">НОВЫЙ</div>' : ''}
            <div class="ticket-status-indicator" style="background: #10b981;"></div>
            <div class="ticket-header-compact">
                <h3>${museumName}</h3>
                <div class="ticket-category-badge">${ticketType}</div>
            </div>
            
            <div class="ticket-body-compact">
                <div class="ticket-info-compact">
                    <div class="info-row-compact">
                        <span class="info-label-compact">Посетитель:</span>
                        <span class="info-value-compact">${visitorName} ${visitorSurname}</span>
                    </div>
                    <div class="info-row-compact">
                        <span class="info-label-compact">Телефон:</span>
                        <span class="info-value-compact">${visitorPhone}</span>
                    </div>
                    <div class="info-row-compact">
                        <span class="info-label-compact">Приобретено:</span>
                        <span class="info-value-compact" style="color: #10b981; font-weight: bold;">${purchaseDate}</span>
                    </div>
                    <div class="info-row-compact">
                        <span class="info-label-compact">Дата посещения:</span>
                        <span class="info-value-compact">${visitDate} ${visitTime}</span>
                    </div>
                    <div class="info-row-compact">
                        <span class="info-label-compact">Сумма:</span>
                        <span class="info-value-compact" style="font-weight: bold; color: #3b82f6;">${price}₽</span>
                    </div>
                </div>
                
                <div class="ticket-number-compact">
                    № ${ticket.ticket_number}
                </div>
                
                <div class="barcode-compact">
                    <img src="${ticket.barcodeDataURL}" alt="Штрих-код" 
                         style="width: 200px; height: 60px; border: 1px solid #ddd; background: white; display: block; margin: 0 auto;">
                    <p style="font-size: 0.7rem; margin-top: 5px; color: #666; text-align: center;">
                        Штрих-код для входа
                    </p>
                </div>
                
                <div class="ticket-actions-compact">
                    <button class="action-btn-compact save-btn-compact" onclick="saveSingleTicket(this)">
                        Сохранить
                    </button>
                    <button class="action-btn-compact share-btn-compact" onclick="shareSingleTicket('${ticket.ticket_number}')">
                        Поделиться
                    </button>
                </div>
            </div>
        </div>
    `}).join('');
    
    ticketsGrid.innerHTML = ticketsHTML;
    
    if (window.newTicketNumbers && window.newTicketNumbers.length > 0) {
        setTimeout(() => {
            const newTickets = document.querySelectorAll('.ticket-card-compact.new-ticket');
            newTickets.forEach(ticket => {
                ticket.classList.remove('new-ticket');
                const badge = ticket.querySelector('.new-ticket-badge');
                if (badge) badge.remove();
            });
            window.newTicketNumbers = [];
            console.log('Подсветка новых билетов убрана');
        }, 7000);
    }
}

function saveSingleTicket(button) {
    const ticketCard = button.closest('.ticket-card-compact');
    if (typeof html2canvas === 'undefined') {
        showMessage('Функция сохранения недоступна');
        return;
    }

    const originalText = button.textContent;
    button.textContent = 'Сохраняем...';
    button.disabled = true;

    const tempContainer = document.createElement('div');
    tempContainer.style.position = 'fixed';
    tempContainer.style.left = '0';
    tempContainer.style.top = '0';
    tempContainer.style.width = '400px';
    tempContainer.style.zIndex = '-1000';
    tempContainer.style.opacity = '0';
    tempContainer.style.pointerEvents = 'none';
    
    const clone = ticketCard.cloneNode(true);
    clone.style.width = '380px';
    clone.style.margin = '10px auto';
    clone.style.background = '#ffffff';
    clone.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.15)';
    
    tempContainer.appendChild(clone);
    document.body.appendChild(tempContainer);

    setTimeout(() => {
        html2canvas(clone, {
            scale: 2,
            useCORS: true,
            logging: false,
            backgroundColor: '#ffffff',
            allowTaint: false,
            width: clone.offsetWidth,
            height: clone.offsetHeight,
            scrollX: 0,
            scrollY: 0
        }).then(canvas => {
            const link = document.createElement('a');
            const ticketNumber = ticketCard.querySelector('.ticket-number-compact')?.textContent?.replace(/[^\w]/g, '') || 'ticket';
            link.download = `билет_${ticketNumber}.png`;
            link.href = canvas.toDataURL('image/png', 1.0);
            
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            document.body.removeChild(tempContainer);
            
            button.textContent = '✓ Сохранено';
            button.style.background = '#10b981';
            setTimeout(() => {
                button.textContent = originalText;
                button.style.background = '';
                button.disabled = false;
            }, 2000);
            
            showMessage('Билет успешно сохранен!');
            
        }).catch(error => {
            console.error('Ошибка при создании изображения:', error);
            document.body.removeChild(tempContainer);
            simpleSaveTicket(ticketCard, button, originalText);
        });
    }, 100);
}

function simpleSaveTicket(ticketCard, button, originalText) {
    const ticketInfo = {
        number: ticketCard.querySelector('.ticket-number-compact')?.textContent || 'Неизвестно',
        museum: ticketCard.querySelector('h3')?.textContent || 'Неизвестный музей',
        visitor: ticketCard.querySelector('.info-value-compact')?.textContent || 'Неизвестно',
        date: Array.from(ticketCard.querySelectorAll('.info-value-compact'))[3]?.textContent || 'Неизвестно'
    };
    
    const content = `
╔═══════════════════════════════╗
║          БИЛЕТ В МУЗЕЙ        ║
╠═══════════════════════════════╣
║ Музей: ${ticketInfo.museum.padEnd(25).substring(0,25)} ║
║ Посетитель: ${ticketInfo.visitor.padEnd(20).substring(0,20)} ║
║ Дата: ${ticketInfo.date.padEnd(24).substring(0,24)} ║
║ Номер: ${ticketInfo.number.padEnd(23).substring(0,23)} ║
║                               ║
║     Предъявите этот номер     ║
║      на входе в музей         ║
╚═══════════════════════════════╝
    `.trim();
    
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const link = document.createElement('a');
    link.download = `билет_${ticketInfo.number.replace(/\s+/g, '')}.txt`;
    link.href = URL.createObjectURL(blob);
    link.click();
    URL.revokeObjectURL(link.href);
    
    button.textContent = originalText;
    button.disabled = false;
    showMessage('Билет сохранен в текстовом формате');
}

function fallbackSaveTicket(ticketCard, button, originalText) {
    const ticketInfo = {
        number: ticketCard.querySelector('.ticket-number-compact')?.textContent || 'Неизвестно',
        museum: ticketCard.querySelector('h3')?.textContent || 'Неизвестный музей',
        visitor: ticketCard.querySelector('.info-value-compact')?.textContent || 'Неизвестно'
    };
    
    const textContent = `Билет ${ticketInfo.number}\nМузей: ${ticketInfo.museum}\nПосетитель: ${ticketInfo.visitor}`;
    const blob = new Blob([textContent], { type: 'text/plain' });
    const link = document.createElement('a');
    link.download = `билет_${Date.now()}.txt`;
    link.href = URL.createObjectURL(blob);
    link.click();
    URL.revokeObjectURL(link.href);
    
    button.textContent = originalText;
    button.disabled = false;
    showMessage('Билет сохранен в текстовом формате');
}

function shareSingleTicket(ticketNumber) {
    if (navigator.share) {
        navigator.share({
            title: 'Мой билет в музей',
            text: `Билет №${ticketNumber}`,
            url: window.location.href
        }).catch(error => {
            console.log('Ошибка при попытке поделиться:', error);
        });
    } else {
        showMessage('Функция "Поделиться" не поддерживается в вашем браузере');
    }
}

function formatDate(dateString) {
    if (!dateString) return '';
    try {
        let date;
        if (dateString.includes('T')) {
            date = new Date(dateString);
        } else {
            date = new Date(dateString + 'T00:00:00');
        }
        
        if (isNaN(date.getTime())) {
            return dateString;
        }
        
        return date.toLocaleDateString('ru-RU');
    } catch (e) {
        console.error('Ошибка форматирования даты:', e);
        return dateString;
    }
}

function formatTime(timeString) {
    if (!timeString) return '';
    try {
        if (timeString.includes(':')) {
            const parts = timeString.split(':');
            if (parts.length >= 2) {
                return `${parts[0]}:${parts[1]}`;
            }
        }
        return timeString;
    } catch (e) {
        console.error('Ошибка форматирования времени:', e);
        return timeString;
    }
}

function formatDateTime(dateTimeString) {
    if (!dateTimeString) return '';
    try {
        const date = new Date(dateTimeString);
        if (isNaN(date.getTime())) {
            return dateTimeString;
        }
        return date.toLocaleDateString('ru-RU') + ' ' + date.toLocaleTimeString('ru-RU', {hour: '2-digit', minute:'2-digit'});
    } catch (e) {
        console.error('Ошибка форматирования даты и времени:', e);
        return dateTimeString;
    }
}

function openQRLink(ticketNumber) {
    alert(`QR код для билета №${ticketNumber}\nВ реальном приложении здесь будет ссылка на проверку билета`);
}

function saveUserToStorage(user) {
    localStorage.setItem('currentUser', JSON.stringify(user));
    console.log('Пользователь сохранен в localStorage');
}

function getUserFromStorage() {
    const userData = localStorage.getItem('currentUser');
    if (userData) {
        console.log('Найден пользователь в localStorage');
        return JSON.parse(userData);
    }
    return null;
}

function removeUserFromStorage() {
    localStorage.removeItem('currentUser');
    console.log('Пользователь удален из localStorage');
}

function startSlotsUpdateInterval() {
    stopSlotsUpdateInterval();
    
    slotsInterval = setInterval(() => {
        if (currentMuseumId && document.getElementById('museum-detail').style.display === 'block') {
            console.log('🔄 Автоматическое обновление количества билетов...');
            generateDateSlots();
        }
    }, 2000);
}

function stopSlotsUpdateInterval() {
    if (slotsInterval) {
        clearInterval(slotsInterval);
        slotsInterval = null;
    }
}

async function saveTicketToDatabase(museum, ticketNumber, ticketCount, totalPrice) {
    if (!currentMuseumId) {
        console.error('Ошибка: museum_code не определен');
        console.log('currentMuseumId:', currentMuseumId);
        showMessage('Ошибка: не выбран музей');
        return;
    }
    
    if (!currentUser || !currentUser.id) {
        console.error('Ошибка: пользователь не авторизован');
        showMessage('Ошибка: пользователь не авторизован');
        return;
    }
    
    if (!selectedDateSlot || !selectedTimeSlot) {
        console.error('Ошибка: не выбрана дата или время');
        showMessage('Ошибка: не выбрана дата или время посещения');
        return;
    }
    
    try {
        const ticketPromises = ticketCategories.map(async (category, index) => {
            const individualTicketNumber = ticketNumber + '-' + (index + 1).toString().padStart(2, '0');
            const multiplier = multipliers[category] || 1.0;
            const individualPrice = Math.round(currentMuseumPrice * multiplier);
            
            const ticketData = {
                ticket_number: individualTicketNumber,
                visitor_id: currentUser.id,
                ticket_type: category,
                price: individualPrice,
                museum_code: currentMuseumId,
                quantity: 1,
                visit_date: selectedDateSlot,
                visit_time: selectedTimeSlot,
                museum_name: museum.title,
                purchase_date: new Date().toISOString()
            };
            
            console.log(`Создание билета ${index + 1}:`, ticketData);
            
            const response = await fetch(`${API_BASE_URL}/api/tickets/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(ticketData)
            });
            
            if (!response.ok) {
                throw new Error(`Ошибка при создании билета ${index + 1}`);
            }
            
            return response.json();
        });
        
        const savedTickets = await Promise.all(ticketPromises);
        console.log('✅ Все билеты успешно созданы:', savedTickets);
        
        await recordSale(currentMuseumId, ticketCount, totalPrice);
        
        showMessage('✅ Билеты успешно созданы и сохранены в базе данных!');
        
    } catch (error) {
        console.error('❌ Ошибка при сохранении билетов:', error);
        showMessage('❌ Ошибка при сохранении билетов: ' + error.message);
    }
}

async function recordSale(museumCode, quantity, totalPrice) {
    try {
        console.log('=== НАЧАЛО ЗАПИСИ ПРОДАЖИ ===');
        console.log('Параметры:', { museumCode, quantity, totalPrice });
        
        console.log('Получаем mapping музеев...');
        const mappingResponse = await fetch(`${API_BASE_URL}/api/museums/mapping`);
        
        if (!mappingResponse.ok) {
            console.error('❌ Не удалось получить mapping музеев. Статус:', mappingResponse.status);
            return;
        }
        
        const museumsMapping = await mappingResponse.json();
        console.log('Получен mapping музеев:', museumsMapping);
        
        const museumId = museumsMapping[museumCode];
        console.log(`Для museum_code "${museumCode}" найден museum_id:`, museumId);
        
        if (!museumId) {
            console.error(`❌ Музей с кодом "${museumCode}" не найден в базе данных`);
            console.log('Доступные коды музеев:', Object.keys(museumsMapping));
            return;
        }
        
        const saleData = {
            museums_id: museumId,
            quantity_tickets_sold: quantity,
            income: totalPrice.toString(),
            date: new Date().toISOString().split('T')[0],
            status: 'online'
        };
        
        console.log('=== ОТПРАВКА ДАННЫХ ПРОДАЖИ ===');
        console.log('Данные:', saleData);
        
        const response = await fetch(`${API_BASE_URL}/api/sales/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(saleData)
        });
        
        console.log('Статус ответа сервера:', response.status);
        
        if (response.ok) {
            const saleResult = await response.json();
            console.log('✅ Продажа записана в таблицу sales:', saleResult);
        } else {
            const errorText = await response.text();
            console.error('❌ Ошибка при записи продажи. Статус:', response.status);
            console.error('Текст ошибки:', errorText);
        }
    } catch (error) {
        console.error('❌ Ошибка сети при записи продажи:', error);
        console.error('Тип ошибки:', error.name);
        console.error('Сообщение ошибки:', error.message);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    const ticketContainer = document.getElementById('ticket-container');
    if (ticketContainer) {
        ticketContainer.innerHTML = '';
        ticketContainer.style.display = 'none';
    }
    
    ticketCategories = ['Стандартный'];
    
    setupPaymentValidation();
    checkAuth();
    updateTotal();
    currentMuseumPrice = museumData['modern-art'].price;
    
    const buyButton = document.querySelector('.buy-button');
    if (buyButton) {
        buyButton.addEventListener('click', buyTickets);
    }
    
    updateTicketCategoriesUI();
    
    const ticketsInput = document.getElementById('tickets');
    if (ticketsInput) {
ticketsInput.addEventListener('change', function() {
    let value = parseInt(this.value);
    
    if (value < 1) {
        this.value = 1;
        value = 1;
    }
    
    if (value > 10) {
        showMessage('Нельзя заказать больше 10 билетов за один раз');
        this.value = 10;
        value = 10;
    }
    
    if (selectedDateSlot && selectedTimeSlot && value > currentAvailableTickets) {
        showMessage(`В выбранном слоте доступно только ${currentAvailableTickets} билетов. Выберите другой слот или уменьшите количество билетов.`);
        this.value = currentAvailableTickets;
        value = currentAvailableTickets;
        
        ticketCategories = ticketCategories.slice(0, currentAvailableTickets);
    }
    
    const currentCount = ticketCategories.length;
    if (value > currentCount) {
        for (let i = currentCount; i < value; i++) {
            ticketCategories.push('Стандартный');
        }
    } else if (value < currentCount) {
        ticketCategories = ticketCategories.slice(0, value);
    }
    
    updateTicketCategoriesUI();
    updateTotal();
});
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const authModal = document.getElementById('auth-modal');
    const paymentModal = document.getElementById('payment-modal');

    setupPaymentValidation();
    
    if (authModal) {
        authModal.addEventListener('click', function(event) {
            if (event.target === authModal) {
                hideAuthModal();
            }
        });
    }
    
    if (paymentModal) {
        paymentModal.addEventListener('click', function(event) {
            if (event.target === paymentModal) {
                closePaymentModal();
            }
        });
    }
    
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            if (authModal && authModal.style.display === 'flex') {
                hideAuthModal();
            }
            if (paymentModal && paymentModal.style.display === 'flex') {
                closePaymentModal();
            }
        }
    });
});
let ticketCategories = ['Стандартный'];

function increaseTickets() {
    const ticketInput = document.getElementById('tickets');
    let currentValue = parseInt(ticketInput.value);
    
    if (currentValue >= 10) {
        showMessage('Нельзя заказать больше 10 билетов за один раз');
        return;
    }
    
    if (selectedDateSlot && selectedTimeSlot) {
        if (currentValue >= currentAvailableTickets) {
            showMessage(`В выбранном слоте доступно только ${currentAvailableTickets} билетов. Выберите другой слот или уменьшите количество билетов.`);
            return;
        }
    }
    
    currentValue++;
    ticketInput.value = currentValue;
    
    ticketCategories.push('Стандартный');
    
    updateTicketCategoriesUI();
    updateTotal();
}

function decreaseTickets() {
    const ticketInput = document.getElementById('tickets');
    let currentValue = parseInt(ticketInput.value);
    if (currentValue > 1) {
        currentValue--;
        ticketInput.value = currentValue;
        
        ticketCategories.pop();
        
        updateTicketCategoriesUI();
        updateTotal();
    }
}

function updateTicketCategoriesUI() {
    const container = document.getElementById('ticket-categories-container');
    if (!container) return;
    
    container.innerHTML = '';
    
    const columnsContainer = document.createElement('div');
    columnsContainer.className = 'ticket-categories-columns';
    
    const totalTickets = ticketCategories.length;
    const firstColumnCount = Math.ceil(totalTickets / 2);
    const secondColumnCount = totalTickets - firstColumnCount;
    
    const firstColumn = document.createElement('div');
    firstColumn.className = 'ticket-categories-column';
    
    for (let i = 0; i < firstColumnCount; i++) {
        const categoryDiv = createCategoryElement(i, ticketCategories[i]);
        firstColumn.appendChild(categoryDiv);
    }
    
    const secondColumn = document.createElement('div');
    secondColumn.className = 'ticket-categories-column';
    
    for (let i = firstColumnCount; i < totalTickets; i++) {
        const categoryDiv = createCategoryElement(i, ticketCategories[i]);
        secondColumn.appendChild(categoryDiv);
    }
    
    columnsContainer.appendChild(firstColumn);
    if (secondColumnCount > 0) {
        columnsContainer.appendChild(secondColumn);
    }
    
    container.appendChild(columnsContainer);
}

function createCategoryElement(index, category) {
    const categoryDiv = document.createElement('div');
    categoryDiv.className = 'ticket-category';
    
    const labelText = index === 0 ? 'Категория билета' : `Категория ${index + 1}-го билета`;
    
    categoryDiv.innerHTML = `
        <label class="font-medium peer-disabled:cursor-not-allowed peer-disabled:opacity-70 text-base">
            ${labelText}
        </label>
        <select class="category-select" data-index="${index}" onchange="updateTicketCategory(${index}, this.value)">
            <option value="Стандартный" ${category === 'Стандартный' ? 'selected' : ''}>Стандартный</option>
            <option value="Льготный" ${category === 'Льготный' ? 'selected' : ''}>Льготный</option>
            <option value="Детский" ${category === 'Детский' ? 'selected' : ''}>Детский</option>
            <option value="Студенческий" ${category === 'Студенческий' ? 'selected' : ''}>Студенческий</option>
            <option value="Пенсионный" ${category === 'Пенсионный' ? 'selected' : ''}>Пенсионный</option>
        </select>
    `;
    
    return categoryDiv;
}

function getTicketNumberText(number) {
    const lastDigit = number % 10;
    const lastTwoDigits = number % 100;
    
    if (lastTwoDigits >= 11 && lastTwoDigits <= 19) {
        return number + '-го';
    }
    
    switch (lastDigit) {
        case 1: return number + '-го';
        case 2: return number + '-го';
        case 3: return number + '-го';
        case 4: return number + '-го';
        default: return number + '-го';
    }
}

function updateTicketCategory(index, category) {
    ticketCategories[index] = category;
    updateTotal();
}