import React from 'react'
import MaroclearWidget from './MaroclearWidget.jsx'

function App() {
  const [messages, setMessages] = React.useState([
    { role: 'assistant', content: "Bonjour ! Je suis l'agent IA de Maroclear. Je peux vous renseigner sur nos services : règlement-livraison, admission des titres, conservation, OST et plus encore." }
  ]);
  const [input, setInput] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [isOpen, setIsOpen] = React.useState(true);
  const messagesEndRef = React.useRef(null);

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  React.useEffect(() => {
    const handleClick = (e) => {
      const link = e.target.closest('a');
      if (!link) return;

      if (link.href?.includes('my.maroclear.com')) {
        e.preventDefault();
        window.open('/my-maroclear.html', '_blank');
      }
    };
    document.addEventListener('click', handleClick);
    return () => document.removeEventListener('click', handleClick);
  }, []);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);
    try {
      const response = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: 'claude-sonnet-4-20250514',
          max_tokens: 1000,
          system: "Tu es l'assistant IA officiel de Maroclear, le dépositaire central des titres au Maroc. Tu réponds en français par défaut. Tu aides sur : affiliation, règlement-livraison, admission des titres, OST, conservation, données de marché. Sois professionnel et concis.",
          messages: [...messages, { role: 'user', content: userMessage }].map(m => ({ role: m.role, content: m.content }))
        })
      });
      const data = await response.json();
      const reply = data.content?.[0]?.text || 'Désolé, une erreur est survenue.';
      setMessages(prev => [...prev, { role: 'assistant', content: reply }]);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Erreur de connexion. Veuillez réessayer.' }]);
    }
    setLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') sendMessage();
  };

  const siteHTML = `
    
        <a href="#main-content" class="visually-hidden focusable">
      Skip to main content
    </a>
    
      <div class="dialog-off-canvas-main-canvas" data-off-canvas-main-canvas="">
    <div class="nav-top bg-dark d-none d-lg-block">
	<div class="mc-container-fluid h-100 text-light">
		<div class="row gx-0 align-items-center justify-content-between h-100">
			<div class="col-auto nav-top-left d-none d-lg-block z-3">
					<nav role="navigation" aria-labelledby="block-maroclear-theme-secondarymenu-menu" id="block-maroclear-theme-secondarymenu">
            
  <h2 class="visually-hidden" id="block-maroclear-theme-secondarymenu-menu">Secondary Menu</h2>
  

        


											<ul class="nav-top-left__links row fw-light gx-6 mb-0 p-0 list-style-none">
									<li class="col-auto">
						<a class="txt-deco-none text-white mc-animate t-hover" href="https://www.maroclear.com/a-propos">About us</a>
					</li>
									<li class="col-auto">
						<a class="txt-deco-none text-white mc-animate t-hover" href="https://www.maroclear.com/en/capital-humain?to=profils-pourvoir">Join us</a>
					</li>
									<li class="col-auto">
						<a class="txt-deco-none text-white mc-animate t-hover" href="https://www.maroclear.com/en/contact">Contact us</a>
					</li>
							</ul>
			

	

  </nav>


			</div>
			<div class="col-12 col-lg-3 nav-top-right z-5">
				<div class="nav-top-right__container row gx-7 justify-content-end align-items-center">
					<div class="col-auto nav-top-right__currency cursor-pointer d-flex column-gap-2 justify-content-center align-items-center"><div class="control-select">
                  <div class="selected-option d-flex text-white column-gap-2 justify-content-center align-items-center">
                    <span class="select-label">MAD</span>
                    <span class="arrow-icon"><img src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/arrow-down.svg" alt="arrow down"></span>
                  </div>
                  <div class="options z-5">
									                    <a class="option d-block text-reset" href="https://www.maroclear.com/change-currency/eur" data-value="EUR"><span class="mc-animate t-hover text-reset">EUR</span></a>
									                  </div>
                </div>
					</div>
									</div>
			</div>
		</div>
	</div>
</div>

<header class="position-sticky top-0 z-4">
	<nav class="nav mc-container-fluid pe-0">
		<div class="row h-100 align-items-center justify-content-between gx-0">
			<div class="col-6 col-lg-auto d-flex align-items-center column-gap-3 gx-0">
				<div class="nav-burger-mobile d-block d-lg-none">
					<button class="border-0 bg-0 p-0 ps-2">
						<img src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/burger.svg" alt="maroclear logo">
					</button>
				</div>
				<div class="nav-logo">	

      <a href="https://www.maroclear.com/en" rel="home">
      <img src="https://www.maroclear.com/sites/default/files/theme/logo.svg" alt="Home" fetchpriority="high">
    </a>
      


<div class="fs-lg-6">
	  
<div id="cookiesjsr"><div class="cookiesjsr--app"></div></div>

</div>

</div>
			</div>
			<div class="col ps-lg-6 nav-menu h-100 d-none d-lg-block">
					<div aria-labelledby="" id="block-maroclear-theme-mainnavigation" class="position-static h-100">
		<div class="w-100 position-relative">
		
	</div>
			
								<ul data-region="primary_menu" class="nav-menu__list ps-0 gx-lg-4 gx-xl-6 row row-cols-lg-auto w-100 h-100 mb-0 justify-content-center list-style-none d-none d-lg-flex">
									<li class="col nav-menu__item mc-animate t-border-color">
						<div data-has-submenu="1" class="nav-menu__link d-flex align-items-center h-100 cursor-pointer">
							<span class="menu-text fs-6" title="Services">Services</span>
															<span class="ms-3 arrow-icon"><img src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/arrow-top-green.svg" alt="menu-icon"></span>
													</div>
													<div class="submenu pt-8 pb-10 pe-8 position-absolute bg-white w-100 start-0 z-9">
								<div class="container-fluid ps-4 pe-3">
									<div class="row">
										<div class="col-4 ps-7 pe-0 d-flex align-items-center">
											<div class="menu-image w-100 h-100 rounded-4 overflow-hidden">
																								<img src="https://www.maroclear.com/sites/default/files/2024-10/service%20%281%29.webp" alt="Menu Services" loadin="lazy" class="w-100 h-100" style="object-fit: cover;">
											</div>
										</div>
										<div class="col-8 ps-9 pe-0">							<ul class="submenu__list row row-cols-2 row-gap-5 p-0 list-style-none">
									<li class="submenu__item col">
						<a class="text-reset" href="https://www.maroclear.com/services/affiliation">
							<div class="d-flex justify-content-between text-dark">
								<p class=" fw-bold fs-6">Affiliation</p>
							</div>

							<hr class="my-2">
							<p class="fw-light">The process by which a financial institution or issuer registers with the Central Depositary to access its services is referred to as affiliation to the services of a Central Depositary.</p>
						</a>

					</li>
									<li class="submenu__item col">
						<a class="text-reset" href="https://www.maroclear.com/services/reglement-livraison">
							<div class="d-flex justify-content-between text-dark">
								<p class=" fw-bold fs-6">Settlement/Delivery</p>
							</div>

							<hr class="my-2">
							<p class="fw-light">The Settlement/Delivery service assists you in the transaction settlement process.</p>
						</a>

					</li>
									<li class="submenu__item col">
						<a class="text-reset" href="https://www.maroclear.com/services/admission-des-titres">
							<div class="d-flex justify-content-between text-dark">
								<p class=" fw-bold fs-6">Admission of securities</p>
							</div>

							<hr class="my-2">
							<p class="fw-light">Admission of securities to a central securities depository refers to the process by which financial securities are registered and recognized in the central securities depository systems for safekeeping and processing.</p>
						</a>

					</li>
									<li class="submenu__item col">
						<a class="text-reset" href="https://www.maroclear.com/services/operations-sur-titres">
							<div class="d-flex justify-content-between text-dark">
								<p class=" fw-bold fs-6">Transactions of securities</p>
							</div>

							<hr class="my-2">
							<p class="fw-light">Securities administration refers to all activities related to the management of events on securities registered with Maroclear.</p>
						</a>

					</li>
									<li class="submenu__item col">
						<a class="text-reset" href="https://www.maroclear.com/services/conservation">
							<div class="d-flex justify-content-between text-dark">
								<p class=" fw-bold fs-6">Conservation</p>
							</div>

							<hr class="my-2">
							<p class="fw-light">Conservation is the process by which the central depositary stores, manages and secures its affiliates' financial securities in electronic format. </p>
						</a>

					</li>
							</ul>
			

										</div>
									</div>
								</div>
							</div>
											</li>
									<li class="col nav-menu__item mc-animate t-border-color">
						<div data-has-submenu="1" class="nav-menu__link d-flex align-items-center h-100 cursor-pointer">
							<span class="menu-text fs-6" title="Data services">Data services</span>
															<span class="ms-3 arrow-icon"><img src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/arrow-top-green.svg" alt="menu-icon"></span>
													</div>
													<div class="submenu pt-8 pb-10 pe-8 position-absolute bg-white w-100 start-0 z-9">
								<div class="container-fluid ps-4 pe-3">
									<div class="row">
										<div class="col-4 ps-7 pe-0 d-flex align-items-center">
											<div class="menu-image w-100 h-100 rounded-4 overflow-hidden">
																								<img src="https://www.maroclear.com/sites/default/files/2024-10/images_big_menu_data_services.webp" alt="Data Service" loadin="lazy" class="w-100 h-100" style="object-fit: cover;">
											</div>
										</div>
										<div class="col-8 ps-9 pe-0">							<ul class="submenu__list row row-cols-2 row-gap-5 p-0 list-style-none">
									<li class="submenu__item col">
						<a class="text-reset" href="https://www.maroclear.com/en/data-services/repository">
							<div class="d-flex justify-content-between text-dark">
								<p class=" fw-bold fs-6">Repository</p>
							</div>

							<hr class="my-2">
							<p class="fw-light">Our data repository provides you with centralized access to accurate and reliable information.</p>
						</a>

					</li>
									<li class="submenu__item col">
						<a class="text-reset" href="https://www.maroclear.com/en/data-services/settled-flows">
							<div class="d-flex justify-content-between text-dark">
								<p class=" fw-bold fs-6">Settled flows</p>
							</div>

							<hr class="my-2">
							<p class="fw-light">Settled flows provide you with a complete and detailed view of the completed transactions, ensuring transparency and accuracy of operations.</p>
						</a>

					</li>
									<li class="submenu__item col">
						<a class="text-reset" href="https://www.maroclear.com/en/data-services/conservation">
							<div class="d-flex justify-content-between text-dark">
								<p class=" fw-bold fs-6">Conservation</p>
							</div>

							<hr class="my-2">
							<p class="fw-light">As the Central Depositary, MAROCLEAR ensures the custody and management of financial securities such as shares, bonds and other financial instruments.</p>
						</a>

					</li>
									<li class="submenu__item col">
						<a class="text-reset" href="https://www.maroclear.com/en/data-services/ost/echeancier">
							<div class="d-flex justify-content-between text-dark">
								<p class=" fw-bold fs-6">OST</p>
							</div>

							<hr class="my-2">
							<p class="fw-light">Securities administration refers to all activities related to the management of events on securities registered with Maroclear.</p>
						</a>

					</li>
							</ul>
			

										</div>
									</div>
								</div>
							</div>
											</li>
									<li class="col nav-menu__item mc-animate t-border-color">
						<div data-has-submenu="1" class="nav-menu__link d-flex align-items-center h-100 cursor-pointer">
							<span class="menu-text fs-6" title="Events and News">Events and News</span>
															<span class="ms-3 arrow-icon"><img src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/arrow-top-green.svg" alt="menu-icon"></span>
													</div>
													<div class="submenu pt-8 pb-10 pe-8 position-absolute bg-white w-100 start-0 z-9">
								<div class="container-fluid ps-4 pe-3">
									<div class="row">
										<div class="col-4 ps-7 pe-0 d-flex align-items-center">
											<div class="menu-image w-100 h-100 rounded-4 overflow-hidden">
																								<img src="https://www.maroclear.com/sites/default/files/2024-10/images_big_menu_%C3%A9v%C3%A8nements.webp" alt="Évènements et actualités" loadin="lazy" class="w-100 h-100" style="object-fit: cover;">
											</div>
										</div>
										<div class="col-8 ps-9 pe-0">							<ul class="submenu__list row row-cols-2 row-gap-5 p-0 list-style-none">
									<li class="submenu__item col">
						<a class="text-reset" href="https://www.maroclear.com/en/events">
							<div class="d-flex justify-content-between text-dark">
								<p class=" fw-bold fs-6">Events and news</p>
							</div>

							<hr class="my-2">
							<p class="fw-light">Find out the latest news and updates on our activities and services.</p>
						</a>

					</li>
									<li class="submenu__item col">
						<a class="text-reset" href="https://www.maroclear.com/en/publications">
							<div class="d-flex justify-content-between text-dark">
								<p class=" fw-bold fs-6">Publications</p>
							</div>

							<hr class="my-2">
							<p class="fw-light">Find all our publications in the press and our press releases.</p>
						</a>

					</li>
							</ul>
			

										</div>
									</div>
								</div>
							</div>
											</li>
									<li class="col nav-menu__item mc-animate t-border-color">
						<div data-has-submenu="1" class="nav-menu__link d-flex align-items-center h-100 cursor-pointer">
							<span class="menu-text fs-6" title="Maroclear">Maroclear</span>
															<span class="ms-3 arrow-icon"><img src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/arrow-top-green.svg" alt="menu-icon"></span>
													</div>
													<div class="submenu pt-8 pb-10 pe-8 position-absolute bg-white w-100 start-0 z-9">
								<div class="container-fluid ps-4 pe-3">
									<div class="row">
										<div class="col-4 ps-7 pe-0 d-flex align-items-center">
											<div class="menu-image w-100 h-100 rounded-4 overflow-hidden">
																								<img src="https://www.maroclear.com/sites/default/files/2024-10/images_big_menu_maroclear.webp" alt="Marclear Menu" loadin="lazy" class="w-100 h-100" style="object-fit: cover;">
											</div>
										</div>
										<div class="col-8 ps-9 pe-0">							<ul class="submenu__list row row-cols-2 row-gap-5 p-0 list-style-none">
									<li class="submenu__item col">
						<a class="text-reset" href="https://www.maroclear.com/en/gouvernance">
							<div class="d-flex justify-content-between text-dark">
								<p class=" fw-bold fs-6">Governance</p>
							</div>

							<hr class="my-2">
							<p class="fw-light"></p>
						</a>

					</li>
									<li class="submenu__item col">
						<a class="text-reset" href="https://www.maroclear.com/en/a-propos">
							<div class="d-flex justify-content-between text-dark">
								<p class=" fw-bold fs-6">About us</p>
							</div>

							<hr class="my-2">
							<p class="fw-light"></p>
						</a>

					</li>
									<li class="submenu__item col">
						<a class="text-reset" href="https://www.maroclear.com/en/vision-strategie">
							<div class="d-flex justify-content-between text-dark">
								<p class=" fw-bold fs-6">Vision and Strategy</p>
							</div>

							<hr class="my-2">
							<p class="fw-light"></p>
						</a>

					</li>
									<li class="submenu__item col">
						<a class="text-reset" href="https://www.maroclear.com/en/capital-humain">
							<div class="d-flex justify-content-between text-dark">
								<p class=" fw-bold fs-6">Human Capital</p>
							</div>

							<hr class="my-2">
							<p class="fw-light"></p>
						</a>

					</li>
									<li class="submenu__item col">
						<a class="text-reset" href="https://www.maroclear.com/en/cadre-reglementaire-legal">
							<div class="d-flex justify-content-between text-dark">
								<p class=" fw-bold fs-6">Regulatory and Legal Framework</p>
							</div>

							<hr class="my-2">
							<p class="fw-light"></p>
						</a>

					</li>
									<li class="submenu__item col">
						<a class="text-reset" href="https://www.maroclear.com/en/missions-valeurs">
							<div class="d-flex justify-content-between text-dark">
								<p class=" fw-bold fs-6">Missions and values</p>
							</div>

							<hr class="my-2">
							<p class="fw-light"></p>
						</a>

					</li>
							</ul>
			

										</div>
									</div>
								</div>
							</div>
											</li>
							</ul>
			
		

	</div>


			</div>
			<div class="col-auto pe-2 d-none d-lg-block">
				<button class="search-btn bg-0 border-0">
					<img src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/loop.svg" alt="Search">
				</button>
			</div>
			<div class="col-5 col-lg-2p5 h-100 gx-0">
				<a href="https://my.maroclear.com" target="_blank" class="btn-espace-mc mc-animate t-primary p-0 d-flex column-gap-2 column-gap-lg-3 align-items-center justify-content-center border-0 text-white fw-medium h-100" type="button">
					<span><img src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/my-maroclear-icon.svg" alt="Espace Maroclear"></span>
					<span class="btn-espace-mc__text">My Maroclear</span>
				</a>
			</div>
		</div>
	</nav>
	<div class="mobile-menu overflow-auto active-menu-link bg-white position-fixed bottom-0 start-0 pb-0 w-100 z-9 d-lg-none">
		<div class="container-fluid p-0 h-100">
			<div class="row  gx-0 flex-nowrap flex-column h-100 gx-0 justify-content-between">
				<div class="col">
					<div class="container-fluid">
						<div class="row align-items-center">
							<div class="col ps-3 text-start">
									

      <a href="https://www.maroclear.com/en" rel="home">
      <img src="https://www.maroclear.com/sites/default/files/theme/logo.svg" alt="Home" fetchpriority="high">
    </a>
      


<div class="fs-lg-6">
	  
<div id="cookiesjsr"></div>

</div>


							</div>
							<div class="col py-3 text-end">
								<button class="border-0 bg-0 search-btn">
									<img src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/loop.svg" alt="search icon">
								</button>
								<button class="border-0 bg-0 close-mobile-menu">
									<img src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/close.svg" alt="close icon">
								</button>
							</div>
						</div>
					</div>
					<div class="container-fluid gx-0  mobile-menu-primary">
						
								<div mobile-display="true" class="menu-links pb-5 row gx-0 row-cols-1 fw-medium">
									<div class="menu-item col">
						<div class="menu-item-link d-flex align-items-center justify-content-between" data-has-submenu="1" title="Services">
							<span class="text-dark me-2">Services</span>
						</div>
													<div class="submenu">
															<ul class="submenu__list row row-cols-1 ps-0 mb-0 gx-0">
									<li class="submenu__item col">
						<a href="https://www.maroclear.com/services/affiliation" class="text-reset h-100 d-flex flex-column justify-content-center">
							<span>Affiliation</span>
						</a>
					</li>
									<li class="submenu__item col">
						<a href="https://www.maroclear.com/services/reglement-livraison" class="text-reset h-100 d-flex flex-column justify-content-center">
							<span>Settlement/Delivery</span>
						</a>
					</li>
									<li class="submenu__item col">
						<a href="https://www.maroclear.com/services/admission-des-titres" class="text-reset h-100 d-flex flex-column justify-content-center">
							<span>Admission of securities</span>
						</a>
					</li>
									<li class="submenu__item col">
						<a href="https://www.maroclear.com/services/operations-sur-titres" class="text-reset h-100 d-flex flex-column justify-content-center">
							<span>Transactions of securities</span>
						</a>
					</li>
									<li class="submenu__item col">
						<a href="https://www.maroclear.com/services/conservation" class="text-reset h-100 d-flex flex-column justify-content-center">
							<span>Conservation</span>
						</a>
					</li>
							</ul>
			
							</div>
											</div>
									<div class="menu-item col">
						<div class="menu-item-link d-flex align-items-center justify-content-between" data-has-submenu="1" title="Data services">
							<span class="text-dark me-2">Data services</span>
						</div>
													<div class="submenu">
															<ul class="submenu__list row row-cols-1 ps-0 mb-0 gx-0">
									<li class="submenu__item col">
						<a href="https://www.maroclear.com/en/data-services/repository" class="text-reset h-100 d-flex flex-column justify-content-center">
							<span>Repository</span>
						</a>
					</li>
									<li class="submenu__item col">
						<a href="https://www.maroclear.com/en/data-services/settled-flows" class="text-reset h-100 d-flex flex-column justify-content-center">
							<span>Settled flows</span>
						</a>
					</li>
									<li class="submenu__item col">
						<a href="https://www.maroclear.com/en/data-services/conservation" class="text-reset h-100 d-flex flex-column justify-content-center">
							<span>Conservation</span>
						</a>
					</li>
									<li class="submenu__item col">
						<a href="https://www.maroclear.com/en/data-services/ost/echeancier" class="text-reset h-100 d-flex flex-column justify-content-center">
							<span>OST</span>
						</a>
					</li>
							</ul>
			
							</div>
											</div>
									<div class="menu-item col">
						<div class="menu-item-link d-flex align-items-center justify-content-between" data-has-submenu="1" title="Events and News">
							<span class="text-dark me-2">Events and News</span>
						</div>
													<div class="submenu">
															<ul class="submenu__list row row-cols-1 ps-0 mb-0 gx-0">
									<li class="submenu__item col">
						<a href="https://www.maroclear.com/en/events" class="text-reset h-100 d-flex flex-column justify-content-center">
							<span>Events and news</span>
						</a>
					</li>
									<li class="submenu__item col">
						<a href="https://www.maroclear.com/en/publications" class="text-reset h-100 d-flex flex-column justify-content-center">
							<span>Publications</span>
						</a>
					</li>
							</ul>
			
							</div>
											</div>
									<div class="menu-item col">
						<div class="menu-item-link d-flex align-items-center justify-content-between" data-has-submenu="1" title="Maroclear">
							<span class="text-dark me-2">Maroclear</span>
						</div>
													<div class="submenu">
															<ul class="submenu__list row row-cols-1 ps-0 mb-0 gx-0">
									<li class="submenu__item col">
						<a href="https://www.maroclear.com/en/gouvernance" class="text-reset h-100 d-flex flex-column justify-content-center">
							<span>Governance</span>
						</a>
					</li>
									<li class="submenu__item col">
						<a href="https://www.maroclear.com/en/a-propos" class="text-reset h-100 d-flex flex-column justify-content-center">
							<span>About us</span>
						</a>
					</li>
									<li class="submenu__item col">
						<a href="https://www.maroclear.com/en/vision-strategie" class="text-reset h-100 d-flex flex-column justify-content-center">
							<span>Vision and Strategy</span>
						</a>
					</li>
									<li class="submenu__item col">
						<a href="https://www.maroclear.com/en/capital-humain" class="text-reset h-100 d-flex flex-column justify-content-center">
							<span>Human Capital</span>
						</a>
					</li>
									<li class="submenu__item col">
						<a href="https://www.maroclear.com/en/cadre-reglementaire-legal" class="text-reset h-100 d-flex flex-column justify-content-center">
							<span>Regulatory and Legal Framework</span>
						</a>
					</li>
									<li class="submenu__item col">
						<a href="https://www.maroclear.com/en/missions-valeurs" class="text-reset h-100 d-flex flex-column justify-content-center">
							<span>Missions and values</span>
						</a>
					</li>
							</ul>
			
							</div>
											</div>
								<div class="menu-item col ">
					<div class="menu-controls-select row row-cols gx-0"> 						<div class="menu-select menu-currency-select d-flex align-items-center justify-content-center" data-menu-target="submenu-currency">
							<div class="position-relative">
								<span>MAD</span>
							</div>
						</div>
											</div>
					<div class="submenu">
						<div class="menu-controls-links active submenu-currency">
							<ul class="submenu__list row row-cols-1 ps-0 mb-0 gx-0">
															<a class="submenu__item text-reset col" href="https://www.maroclear.com/change-currency/eur">
									<span class="text-reset h-100 d-flex flex-column justify-content-center">EUR </span>
								</a>
															</ul>
						</div>
							<div class="menu-controls-links submenu-language">
		<ul class="submenu__list row row-cols-1 ps-0 mb-0 gx-0">
												<a class="submenu__item col text-reset" href="https://www.maroclear.com/fr">
				<span class="h-100 d-flex flex-column justify-content-center">FR</span>
			</a>
														<a class="submenu__item col text-reset" href="https://www.maroclear.com/ar">
				<span class="h-100 d-flex flex-column justify-content-center">AR</span>
			</a>
			
		</ul>
	</div>

					</div>

				</div>
			</div>
			

	
	

					</div>
				</div>
				<div class="col mobile-menu-secondary pb-3">
					<div class="container-fluid h-100">
						

								<div mobile-display="true" class="container-fluid h-100">
				<div class="row flex-column row-gap-4 h-100">
											<div class="col-auto">
							<a class="btn btn-primary align-items-center justify-content-center mc-animate t-primary icon-link w-100" href="https://www.maroclear.com/a-propos" title="About us">
								About us
							</a>
						</div>
											<div class="col-auto">
							<a class="btn btn-primary align-items-center justify-content-center mc-animate t-primary icon-link w-100" href="https://www.maroclear.com/en/capital-humain?to=profils-pourvoir" title="Join us">
								Join us
							</a>
						</div>
											<div class="col-auto">
							<a class="btn btn-primary align-items-center justify-content-center mc-animate t-primary icon-link w-100" href="https://www.maroclear.com/en/contact" title="Contact us">
								Contact us
							</a>
						</div>
									</div>
			</div>
			

	


					</div>
				</div>
			</div>
		</div>
	</div>
</header>
<div class="mc-search overflow-auto">
	<div class="d-flex justify-content-center w-100 h-100">
		<div class="mc-search__close text-white cursor-pointer">
			<svg class="icon-close-search" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg">
				<path d="M1.66683 14.7916L0.208496 13.3333L6.04183 7.49992L0.208496 1.66659L1.66683 0.208252L7.50016 6.04159L13.3335 0.208252L14.7918 1.66659L8.9585 7.49992L14.7918 13.3333L13.3335 14.7916L7.50016 8.95825L1.66683 14.7916Z" fill="currentcolor"></path>
			</svg>
		</div>
		<div class="views-element-container"><div class="js-view-dom-id-199269f540ff99441d48c99116adc0406ecadeedc4823ce3abb458fe0019bf42 mc-search__body" data-once="ajax-pager">
	<div class="mc-search__header d-flex align-items-center text-white">
		<svg viewBox="0 0 21 21" fill="none" xmlns="http://www.w3.org/2000/svg">
			<path d="M19.9399 18.348L15.4877 13.8939C16.8226 12.1544 17.4458 9.97216 17.2309 7.78998C17.0161 5.60781 15.9792 3.58907 14.3306 2.14328C12.6821 0.697486 10.5453 -0.0670986 8.35376 0.00462578C6.16221 0.0763502 4.07999 0.979013 2.5295 2.5295C0.979013 4.07999 0.0763502 6.16221 0.00462578 8.35376C-0.0670986 10.5453 0.697486 12.6821 2.14328 14.3306C3.58907 15.9792 5.60781 17.0161 7.78998 17.2309C9.97216 17.4458 12.1544 16.8226 13.8939 15.4877L18.3499 19.9445C18.4545 20.0492 18.5787 20.1322 18.7155 20.1888C18.8522 20.2455 18.9987 20.2746 19.1467 20.2746C19.2947 20.2746 19.4413 20.2455 19.578 20.1888C19.7147 20.1322 19.839 20.0492 19.9436 19.9445C20.0482 19.8399 20.1313 19.7157 20.1879 19.5789C20.2445 19.4422 20.2737 19.2957 20.2737 19.1477C20.2737 18.9997 20.2445 18.8531 20.1879 18.7164C20.1313 18.5797 20.0482 18.4554 19.9436 18.3508L19.9399 18.348ZM2.26891 8.64392C2.26891 7.38306 2.6428 6.15052 3.3433 5.10215C4.04379 4.05379 5.03943 3.23669 6.20431 2.75418C7.36919 2.27167 8.65099 2.14543 9.88762 2.39141C11.1242 2.63739 12.2602 3.24455 13.1517 4.13611C14.0433 5.02767 14.6504 6.16359 14.8964 7.40021C15.1424 8.63684 15.0162 9.91864 14.5336 11.0835C14.0511 12.2484 13.234 13.244 12.1857 13.9445C11.1373 14.645 9.90477 15.0189 8.64392 15.0189C6.95369 15.0172 5.3332 14.345 4.13803 13.1498C2.94286 11.9546 2.27065 10.3341 2.26891 8.64392Z" fill="currentcolor"></path>
		</svg>

		<span class="fs-lg-6">Search</span>
	</div>
	<div class="mc-search__form">
		<form class="views-exposed-form" data-drupal-selector="views-exposed-form-se-block" action="/en/home" method="get" id="views-exposed-form-se-block" accept-charset="UTF-8" data-once="exposed-form">
      <input data-drupal-selector="edit-search-api-fulltext" type="text" id="edit-search-api-fulltext" name="search_api_fulltext" value="" size="30" maxlength="128" class="form-text input--search" autocomplete="off" placeholder="Enter your search criteria...">

<input hidden="" id="edit-submit-se" type="submit">
<div class="loader-container"></div>

</form>

	</div>
	<div class="mc-search__results">
		<div class="d-flex justify-content-between column-gap-2">
			<div class="results-description fs-lg-6">
							</div>
			<a href="https://www.maroclear.com/en/glossaire" class="open-glossaire flex-end text-decoration-underline fs-lg-6">Open the glossary </a>
		</div>
		
			</div>
</div>



</div>

	</div>
</div>

<style>
.reglementation .reglementation-swiper .swiper-slide.swiper-slide-visible.swiper-slide-fully-visible.swiper-slide-active {
	 backface-visibility: hidden;
	 transform: translateZ(0) !important;
	
}
.avis .avis-bg .bg-bottom-mobile img { 
	max-width: 430px;
}
</style>
	
		

<div class="fs-lg-6">
	<!-- Main Section - START -->
<section class="main-section position-relative">
	
	<div class="main-section__content mc-container-fluid gx-0 px-lg-0">
		<div class="row gx-0 flex-column flex-lg-row">
			<div class="col order-0 main-section__text-content col-lg-5 text-white row gx-0  pe-lg-6 align-items-center justify-content-xs-center justify-content-lg-start">
				<div class="col-auto text-center text-lg-start px-4 px-lg-0 d-flex d-lg-block flex-column align-items-center">
					<h1 class="main-section__title fs-6 fw-normal mb-4 mb-lg-8 mc-animate fade-in-up op-0" style="opacity: 0.987;">MAROCLEAR, Central Depository and infrastructure serving the development of capital markets.</h1>
					<p class="main-section__subtitle fw-bold fs-2 fs-lg-1 mb-5 mc-animate fade-in-up op-0" style="opacity: 0.987;">
						BUILDING TRUST
					</p>
					<a href="https://www.maroclear.com/en/a-propos" class="main-section__savoir-plus mb-4 mc-animate fade-in-up op-0 delay btn btn-primary icon-link mc-animate t-primary justify-content-center w-100" style="opacity: 0.987;">
						<span>Learn more</span>
					</a>
				</div>
			</div>
			<div class="col order-2 order-lg-1 mc-animate fade-in-right fast op-0" style="opacity: 0.987;">
				<div class="chiffre-marche">
					<div class="chiffre-marche__title bg-white row flex-row-reverse flex-lg-row gx-0 py-2 py-lg-3 align-items-center">
						<div class="col-auto chiffre-marche__icon d-none d-lg-block px-4 ps-lg-6 pe-lg-5">
							<img src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/chiffre-marche-icon.svg" alt="chiffre marche">
						</div>
						<div class="col px-4 px-lg-0">
							<p class="m-0 fw-bold fs-lg-4">
								Central depository activity figures
							</p>
													</div>
					</div>
					<div class="chiffre-marche__content d-none d-lg-block">
						<div class="row row-cols-4 gx-4 ">
							<div class="col-12 content-item mb-3 position-relative">
								<p class="content-item__title fs-6 fw-bold mb-0">Capitalization in billions  (MAD) as of 30/01/2026</p>
								<div class="tooltip-text">
        <p>Capitalisation is calculated according to the LVs and prices, otherwise the nominal value</p>
    </div>
							</div>
							<div class="col content-item mb-5">
								<img class="mb-3" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/money-coins.svg" alt="money-coins">
								<p class="content-item__title fs-6 mb-0">Assets Held</p>
								<p class="content-item__number number-ltr  fw-bold mb-0 fs-6">
									2 884
								</p>
							</div>
							<div class="col content-item mb-5">
								<img class="mb-3" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/money-2.svg" alt="money-coins">
								<p class="content-item__title fs-6 mb-0">Debt Securities</p>
								<p class="content-item__number number-ltr  fw-bold mb-0 fs-6">
									915
								</p>
							</div>
							<div class="col content-item mb-5">
								<img class="mb-3" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/money-1.svg" alt="money-coins">
								<p class="content-item__title fs-6 mb-0">Orga. de Placement Collectif</p>
								<p class="content-item__number number-ltr  fw-bold mb-0 fs-6">
									850
								</p>
							</div>
							<div class="col content-item mb-5">
								<img class="mb-3" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/chart.svg" alt="money-coins">
								<p class="content-item__title fs-6 mb-0">Actions</p>
								<p class="content-item__number number-ltr  fw-bold mb-0 fs-6">
									1 063
								</p>
							</div>
							<div class="col-12 content-item mb-6">
								<p class="content-item__title fs-6 fw-bold mb-0">
									Settled Volume in Millions (MAD) the 04/03/2026
								</p>
							</div>
							<div class="col content-item">
								<img class="mb-3" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/growth.svg" alt="money-coins">
								<p class="content-item__title fs-6 mb-0">Settled Volume</p>
								<p class="content-item__number number-ltr  fw-bold mb-0 fs-6">
									65 529
								</p>
							</div>
							<div class="col content-item">
								<img class="mb-3" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/pension_livree.svg" alt="money-coins">
								<p class="content-item__title fs-6 mb-0">Delivered Repo</p>
								<p class="content-item__number number-ltr  fw-bold mb-0 fs-6">
									48 681
								</p>
							</div>
							<div class="col content-item">
								<img class="mb-3" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/investor.svg" alt="money-coins">
								<p class="content-item__title fs-6 mb-0">Over-the-Counter Transactions</p>
								<p class="content-item__number number-ltr  fw-bold mb-0 fs-6">
									14 632
								</p>
							</div>
							<div class="col content-item">
								<img class="mb-3" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/budget.svg" alt="money-coins">
								<p class="content-item__title fs-6 mb-0">Opérations bourse
								</p>
								<p class="content-item__number number-ltr  fw-bold mb-0 fs-6">
									2 216
								</p>
							</div>
													</div>
					</div>
					<div class="chiffre-marche-mobile d-lg-none row py-5 gx-0 overflow-hidden align-items-stretch">
						<div class="col-2 d-flex align-items-center cm-button-prev ps-5 text-primary" tabindex="0" role="button" aria-label="Previous slide" aria-controls="swiper-wrapper-83a4a10f4104895566" aria-disabled="false">
							<svg class="rotate-0" width="9" height="15" viewBox="0 0 9 15" fill="none" xmlns="http://www.w3.org/2000/svg">
								<path fillRule="evenodd" clip-rule="evenodd" d="M1.8 0L9 7.5L1.8 15L0 13.125L5.4 7.5L0 1.875L1.8 0Z" fill="currentcolor"></path>
							</svg>
						</div>
						<div class="col-8">
							<p class="fw-bold text-center mb-4">Capitalization in billions (MAD) as of 30/01/2026</p>
							<div class="chiffre-marche-mobile-swiper swiper mb-4 swiper-initialized swiper-horizontal">
								<div class="swiper-wrapper" id="swiper-wrapper-4d6b9610b3563c3dc" aria-live="polite" style="transition-duration: 0ms; transition-delay: 0ms;">
									<div class="swiper-slide text-center">
										<img class="mb-1" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/money-coins.svg" alt="money-coins">
										<p class="content-item__title mb-0">Assets Held</p>
										<p class="content-item__number number-ltr  text-center fw-bold mb-0">
											2 884
										</p>
									</div>
									<div class="swiper-slide text-center">
										<img class="mb-1" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/money-2.svg" alt="money-coins">
										<p class="content-item__title mb-0">Debt Securities</p>
										<p class="content-item__number number-ltr  text-center fw-bold mb-0">
											915
										</p>
									</div>
									<div class="swiper-slide text-center">
										<img class="mb-1" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/money-1.svg" alt="money-coins">
										<p class="content-item__title mb-0">Orga. de Placement Collectif</p>
										<p class="content-item__number number-ltr  text-center fw-bold mb-0">
											850
										</p>
									</div>
									<div class="swiper-slide text-center">
										<img class="mb-1" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/chart.svg" alt="money-coins">
										<p class="content-item__title mb-0">Actions</p>
										<p class="content-item__number number-ltr  text-center fw-bold mb-0">
											1 063
										</p>
									</div>
								</div>
							<span class="swiper-notification" aria-live="assertive" aria-atomic="true"></span></div>
							<p class="fw-bold text-center mb-4">Settled Volume in Millions (MAD) the 04/03/2026</p>
							<div class="chiffre-marche-mobile-swiper swiper swiper-initialized swiper-horizontal">
								<div class="swiper-wrapper" id="swiper-wrapper-83a4a10f4104895566" aria-live="polite" style="transition-duration: 0ms; transition-delay: 0ms;">
									<div class="swiper-slide text-center">
										<img class="mb-1" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/growth.svg" alt="money-coins">
										<p class="content-item__title mb-0">Settled Volume</p>
										<p class="content-item__number number-ltr  text-center fw-bold mb-0">
											65 529
										</p>
									</div>
									<div class="swiper-slide text-center">
										<img class="mb-1" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/pension_livree.svg" alt="money-coins">
										<p class="content-item__title mb-0">Delivered Repo</p>
										<p class="content-item__number number-ltr  text-center fw-bold mb-0">
											48 681
										</p>
									</div>
									<div class="swiper-slide text-center">
										<img class="mb-1" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/investor.svg" alt="money-coins">
										<p class="content-item__title mb-0">Over-the-Counter Transactions</p>
										<p class="content-item__number number-ltr  text-center fw-bold mb-0">
											14 632
										</p>
									</div>
									<div class="swiper-slide text-center">
										<img class="mb-1" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/budget.svg" alt="money-coins">
										<p class="content-item__title mb-0">Opérations bourse
										</p>
										<p class="content-item__number number-ltr  text-center fw-bold mb-0">
											2 216
										</p>
									</div>
								</div>
							<span class="swiper-notification" aria-live="assertive" aria-atomic="true"></span></div>
						</div>
						<div class="col-2 d-flex align-items-center text-end cm-button-next pe-5 text-primary justify-content-end" tabindex="0" role="button" aria-label="Next slide" aria-controls="swiper-wrapper-83a4a10f4104895566" aria-disabled="false">
							<svg class="rotate-to-left" width="9" height="15" viewBox="0 0 9 15" fill="none" xmlns="http://www.w3.org/2000/svg">
								<path fillRule="evenodd" clip-rule="evenodd" d="M1.8 0L9 7.5L1.8 15L0 13.125L5.4 7.5L0 1.875L1.8 0Z" fill="currentcolor"></path>
							</svg>
						</div>
											</div>
				</div>
			</div>
			<div class="col-12 infinite-loop-banner order-1 order-lg-1 position-relative">
				<div class="banner-title-wrapper w-100 d-flex justify-content-center">
					<div class="banner-title text-center text-lg-start d-none d-lg-flex align-items-center">
						<p class="fs-lg-6 fw-bold text-white">OST de la semaine</p>
					</div>
				</div>
				<div class="stock-updates-carousel d-flex column-gap-7 text-white">
					<div class="carousel-primary mc-animate infinite-loop" style="translate: none; rotate: none; scale: none; transform: translate(-11.5041%, -50%) translate3d(0px, 0px, 0px);">
													<div class="flex-grow-1 ps-1">
								<span class="rectangle-shape"></span>
								<p class="stock-updates-carousel__text fw-light d-inline-block me-20 mb-0 fs-lg-6 ">
									27/02/2026 - Paiement d'intérêt sur la valeur /Remboursement de capital sur la valeur - <a href="https://www.maroclear.com/en/data-services/ost/echeancier?code=MA0001009812" style="color:#fff;text-decoration:underline;">MA0001009812</a>
								</p>
							</div>
													<div class="flex-grow-1 ps-1">
								<span class="rectangle-shape"></span>
								<p class="stock-updates-carousel__text fw-light d-inline-block me-20 mb-0 fs-lg-6 ">
									27/02/2026 - Paiement d'intérêt sur la valeur /Remboursement de capital sur la valeur - <a href="https://www.maroclear.com/en/data-services/ost/echeancier?code=MA0001531112" style="color:#fff;text-decoration:underline;">MA0001531112</a>
								</p>
							</div>
													<div class="flex-grow-1 ps-1">
								<span class="rectangle-shape"></span>
								<p class="stock-updates-carousel__text fw-light d-inline-block me-20 mb-0 fs-lg-6 ">
									27/02/2026 - Paiement d'intérêt sur la valeur /Remboursement de capital sur la valeur - <a href="https://www.maroclear.com/en/data-services/ost/echeancier?code=MA0001009820" style="color:#fff;text-decoration:underline;">MA0001009820</a>
								</p>
							</div>
													<div class="flex-grow-1 ps-1">
								<span class="rectangle-shape"></span>
								<p class="stock-updates-carousel__text fw-light d-inline-block me-20 mb-0 fs-lg-6 ">
									20/02/2026 - Paiement d'intérêt sur la valeur /Remboursement de capital sur la valeur - <a href="https://www.maroclear.com/en/data-services/ost/echeancier?code=MA0001531377" style="color:#fff;text-decoration:underline;">MA0001531377</a>
								</p>
							</div>
													<div class="flex-grow-1 ps-1">
								<span class="rectangle-shape"></span>
								<p class="stock-updates-carousel__text fw-light d-inline-block me-20 mb-0 fs-lg-6 ">
									20/02/2026 - Paiement d'intérêt sur la valeur /Remboursement de capital sur la valeur - <a href="https://www.maroclear.com/en/data-services/ost/echeancier?code=MA0001531377" style="color:#fff;text-decoration:underline;">MA0001531377</a>
								</p>
							</div>
													<div class="flex-grow-1 ps-1">
								<span class="rectangle-shape"></span>
								<p class="stock-updates-carousel__text fw-light d-inline-block me-20 mb-0 fs-lg-6 ">
									20/02/2026 - Paiement d'intérêt sur la valeur /Remboursement de capital sur la valeur - <a href="https://www.maroclear.com/en/data-services/ost/echeancier?code=MA0001530593" style="color:#fff;text-decoration:underline;">MA0001530593</a>
								</p>
							</div>
											</div>
				<div class="carousel-primary mc-animate infinite-loop" style="translate: none; rotate: none; scale: none; transform: translate(89.2959%, -50%) translate3d(0px, 0px, 0px);">
													<div class="flex-grow-1 ps-1">
								<span class="rectangle-shape"></span>
								<p class="stock-updates-carousel__text fw-light d-inline-block me-20 mb-0 fs-lg-6 ">
									27/02/2026 - Paiement d'intérêt sur la valeur /Remboursement de capital sur la valeur - <a href="https://www.maroclear.com/en/data-services/ost/echeancier?code=MA0001009812" style="color:#fff;text-decoration:underline;">MA0001009812</a>
								</p>
							</div>
													<div class="flex-grow-1 ps-1">
								<span class="rectangle-shape"></span>
								<p class="stock-updates-carousel__text fw-light d-inline-block me-20 mb-0 fs-lg-6 ">
									27/02/2026 - Paiement d'intérêt sur la valeur /Remboursement de capital sur la valeur - <a href="https://www.maroclear.com/en/data-services/ost/echeancier?code=MA0001531112" style="color:#fff;text-decoration:underline;">MA0001531112</a>
								</p>
							</div>
													<div class="flex-grow-1 ps-1">
								<span class="rectangle-shape"></span>
								<p class="stock-updates-carousel__text fw-light d-inline-block me-20 mb-0 fs-lg-6 ">
									27/02/2026 - Paiement d'intérêt sur la valeur /Remboursement de capital sur la valeur - <a href="https://www.maroclear.com/en/data-services/ost/echeancier?code=MA0001009820" style="color:#fff;text-decoration:underline;">MA0001009820</a>
								</p>
							</div>
													<div class="flex-grow-1 ps-1">
								<span class="rectangle-shape"></span>
								<p class="stock-updates-carousel__text fw-light d-inline-block me-20 mb-0 fs-lg-6 ">
									20/02/2026 - Paiement d'intérêt sur la valeur /Remboursement de capital sur la valeur - <a href="https://www.maroclear.com/en/data-services/ost/echeancier?code=MA0001531377" style="color:#fff;text-decoration:underline;">MA0001531377</a>
								</p>
							</div>
													<div class="flex-grow-1 ps-1">
								<span class="rectangle-shape"></span>
								<p class="stock-updates-carousel__text fw-light d-inline-block me-20 mb-0 fs-lg-6 ">
									20/02/2026 - Paiement d'intérêt sur la valeur /Remboursement de capital sur la valeur - <a href="https://www.maroclear.com/en/data-services/ost/echeancier?code=MA0001531377" style="color:#fff;text-decoration:underline;">MA0001531377</a>
								</p>
							</div>
													<div class="flex-grow-1 ps-1">
								<span class="rectangle-shape"></span>
								<p class="stock-updates-carousel__text fw-light d-inline-block me-20 mb-0 fs-lg-6 ">
									20/02/2026 - Paiement d'intérêt sur la valeur /Remboursement de capital sur la valeur - <a href="https://www.maroclear.com/en/data-services/ost/echeancier?code=MA0001530593" style="color:#fff;text-decoration:underline;">MA0001530593</a>
								</p>
							</div>
											</div></div>

			</div>
		</div>
	</div>
</section>
<!-- Main Section - END -->

</div>


<div class="fs-lg-6">
	<!-- Chiffre de l'activité - START -->

	<section class="chiffre-activite mc-container-fluid py-6 py-lg-10 mc-animate fade-on-scroll z-3 position-relative" style="translate: none; rotate: none; scale: none; transform: translate(0px, 100px); opacity: 0;">
	
		<div class="d-flex flex-column row-gap-5 flex-lg-row justify-content-center align-items-center justify-content-lg-between mb-6">
			<h2 class="mb-0">Activity figures</h2>
			<a href="https://www.maroclear.com/data-services/referentiel" class="d-none d-lg-inline-flex btn btn-primary justify-content-center mc-animate t-primary icon-link">
				<span>Consult the detailed report</span>
			</a>
		</div>
		<hr class="py-1">
		<div class="load-data-home">
																												
		<div class="row mt-6 mb-4">
			<div class="col-sm-6 col-xs-12 mb-3">
               <div class="mc-select chiffre-activite-select custom-processed" data-type="input">
                  <input hidden="" type="text" name="cat" id="categorie-filter">
                  <div class="mc-select__selected-value">
                     <span class="fw-medium">Evolution of retained assets</span>
                     <svg class="bi" width="8" height="12" viewBox="0 0 8 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path fillRule="evenodd" clip-rule="evenodd" d="M1.5 0L7.5 6L1.5 12L0 10.5L4.5 6L0 1.5L1.5 0Z" fill="currentcolor"></path>
                     </svg>
                  </div>
                  <div class="mc-select__options-list">
                     <div class="select-options-wrapper">
                        <ul class="mc-select__items-options">
                           <li data-value="capitalisation" data-lang="en" class="mc-select__option selected">
                              <span>Evolution of retained assets</span>
                           </li>
						    <li data-value="moyenne" data-lang="en" class="mc-select__option">
                              <span>Evolution of Settled flows</span>
                           </li>
						                             
                        </ul>
                     </div>
                  </div>
               </div>
            </div>
			<div class="col-sm-6 col-xs-12 mb-3">
               <div class="mc-select chiffre-activite-chart custom-processed" data-type="input">
                  <input hidden="" type="text" name="chart-val" id="chart-val" onchange="updateChart()">
                  <div class="mc-select__selected-value">
                     <span class="fw-medium">Total</span>
                     <svg class="bi" width="8" height="12" viewBox="0 0 8 12" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path fillRule="evenodd" clip-rule="evenodd" d="M1.5 0L7.5 6L1.5 12L0 10.5L4.5 6L0 1.5L1.5 0Z" fill="currentcolor"></path>
                     </svg>
                  </div>
                  <div class="mc-select__options-list">
                     <div class="select-options-wrapper">
                        <ul class="mc-select__items-options">
                           <li data-value="Total" data-color="#F1EDED" data-text="Total" class="mc-select__option selected Total">
                              <span>Total</span>
                           </li>
						   <li data-value="ACTIONS" data-color="#E9CB52" data-text="Actions" class="mc-select__option Actions">
                              <span>Actions</span>
                           </li>
						   <li data-value="DETTE PUBLIC" data-color="#C3DB61" data-text="Bons du trésor" class="mc-select__option Bondutresor">
                              <span>Bons du trésor</span>
                           </li>
						   <li data-value="FPCT" data-color="#8FE063" data-text="FPCT" class="mc-select__option FPCT">
                              <span>FPCT</span>
                           </li>
						   <li data-value="OBLIGATIONS" data-color="#6FC1C6" data-text="Obligations" class="mc-select__option Obligations">
                              <span>Obligations</span>
                           </li>
						   <li data-value="TCN" data-color="#F7A35C" data-text="TCN" class="mc-select__option TCN">
                              <span>TCN</span>
                           </li>
						   <li data-value="OPCI|OPCR" data-color="#B37FC3" data-text="OPCI &amp; OPCC" class="mc-select__option OPCIOPCC">
                              <span>OPCI &amp; OPCC</span>
                           </li>
						   <li data-value="OPCVM ACTIONS|OPCVM CONTRACTUELS|OPCVM DIVERSIFIES|OPCVM MONETAIRES|OPCVM OBLIGATION CT|OPCVM OBLIGATION MT" data-color="#D45A7A" data-text="OPCVM" class="mc-select__option OPCVM">
                              <span>OPCVM</span>
                           </li>
                        </ul>
                     </div>
                  </div>
               </div>
            </div>
		</div>
		<div class="row">
			<div class="col-md-12 mb-4">
				<div id="customLegend" class="custom-legend"><div class="legend-item" style="display: flex; align-items: center; cursor: pointer; margin-bottom: 8px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: rgb(233, 203, 82); margin-right: 4px; margin-left: 4px; border-radius: 100%;"></span><span>Actions</span></div><div class="legend-item" style="display: flex; align-items: center; cursor: pointer; margin-bottom: 8px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: rgb(195, 219, 97); margin-right: 4px; margin-left: 4px; border-radius: 100%;"></span><span>Bons du trésor</span></div><div class="legend-item" style="display: flex; align-items: center; cursor: pointer; margin-bottom: 8px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: rgb(143, 224, 99); margin-right: 4px; margin-left: 4px; border-radius: 100%;"></span><span>FPCT</span></div><div class="legend-item" style="display: flex; align-items: center; cursor: pointer; margin-bottom: 8px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: rgb(111, 193, 198); margin-right: 4px; margin-left: 4px; border-radius: 100%;"></span><span>Obligations</span></div><div class="legend-item" style="display: flex; align-items: center; cursor: pointer; margin-bottom: 8px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: rgb(247, 163, 92); margin-right: 4px; margin-left: 4px; border-radius: 100%;"></span><span>TCN</span></div><div class="legend-item" style="display: flex; align-items: center; cursor: pointer; margin-bottom: 8px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: rgb(179, 127, 195); margin-right: 4px; margin-left: 4px; border-radius: 100%;"></span><span>OPCI &amp; OPCC</span></div><div class="legend-item" style="display: flex; align-items: center; cursor: pointer; margin-bottom: 8px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: rgb(212, 90, 122); margin-right: 4px; margin-left: 4px; border-radius: 100%;"></span><span>OPCVM</span></div><div class="legend-item" style="display: flex; align-items: center; cursor: pointer; margin-bottom: 8px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: rgb(241, 237, 237); margin-right: 4px; margin-left: 4px; border-radius: 100%;"></span><span>Total</span></div></div>
				<div class="position-relative" style="height:500px">	
					<canvas id="lineChart" width="1070" height="500" style="display: block; box-sizing: border-box; height: 500px; width: 1070.8px;"></canvas>
				</div>
			</div>
					</div>
		
	
			</div>
		<div class="row d-lg-none justify-content-center">
			<div class="col col-sm-10 col-md-8">
				<a href="https://www.maroclear.com/data-services/referentiel" class="btn w-100 btn-primary justify-content-center mc-animate t-primary icon-link">
					<span>Consult the detailed report</span>
				</a>
			</div>
		</div>
		<div class="d-none loader-ajax">
		   <svg version="1.1" id="L4" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" viewBox="0 0 100 100" enable-background="new 0 0 0 0" xml:space="preserve">
			  <circle fill="#f5821f" stroke="none" cx="6" cy="50" r="6">
				 <animate attributeName="opacity" dur="1s" values="0;1;0" repeatCount="indefinite" begin="0.1"></animate>
			  </circle>
			  <circle fill="#f5821f" stroke="none" cx="26" cy="50" r="6">
				 <animate attributeName="opacity" dur="1s" values="0;1;0" repeatCount="indefinite" begin="0.2"></animate>
			  </circle>
			  <circle fill="#f5821f" stroke="none" cx="46" cy="50" r="6">
				 <animate attributeName="opacity" dur="1s" values="0;1;0" repeatCount="indefinite" begin="0.3"></animate>
			  </circle>
		   </svg>
		</div>
	</section>
	
</div>


<div class="fs-lg-6">
	<div><!-- Chiffre de l'activité - END -->


<section class="js-view-dom-id-c53a9129b71bb1fd823ab972b6d841fb3eb96342dccbbfe2c1ad974e28c892e5 avis bg-dark position-relative mc-animate fade-on-scroll" data-once="ajax-pager" style="translate: none; rotate: none; scale: none; transform: translate(0px, 100px); opacity: 0;">
	
	<div class="mc-container-fluid position-relative z-3">
		<div class="row">
			<div class="col-12 col-lg-4 text-center d-flex d-lg-block align-items-center flex-column  text-lg-start text-white pe-5">
				<h2 class="mb-5">Notices to affiliates</h2>
				<div class="mb-0 mb-lg-7 fs-lg-6 fw-light text-justify" style="max-width: 445px"><p>Maroclear's "Notices" make it possible to inform market participants (investors, issuers, financial intermediaries) of events related to securities and contribute to better transparency and the proper functioning of the Moroccan financial market.</p></div>
							<a style="min-width:314px;" href="https://www.maroclear.com/en/cadre-reglementaire-legal?to=avis" class="d-none d-lg-inline-flex text-center justify-content-center fs-lg-6 fw-medium btn btn-primary mc-animate t-primary icon-link">
		<span>View all reviews</span>
	</a>

			</div>
			<div class="col-12 col-lg-8 avis-cards-list avis-section light-hover mt-lg-6">
				<div class="row d-none d-lg-flex avis-list-section mc-animate fade-in-up delay-items" style="">
											
											<div class="col-12 col-lg-4" style="opacity: 0.987;">
							<div class="avis-card position-relative mx-auto rounded-3 h-100 d-lg-flex flex-column">
								<div class="card-header px-5 border-bottom border-1">
									<p class="fs-6 text-primary ff-century-gothic">
										<span>Casablanca</span>
										<span class="text-secondary px-3">|</span>
										<span>06/01/2025</span>
									</p>
								</div>
								<div class="card-body px-5 py-4 d-flex flex-column h-100">
									<h5 class="avis-title fw-bold fs-6 ff-century-gothic">
										<a class="text-reset" target="_blank" href="https://www.maroclear.com/sites/default/files/avis/2025-01/DO_AVIS_Avis_MCL_20243112_v3.1.pdf">MAROCLEAR NOTICE N° 594/2024</a>
									</h5>
									<div class="mt-5">
										<p class="fw-light fs-6"></p>
										<div class="download-avis position-lg-absolute z-2">
											<a target="_blank" href="https://www.maroclear.com/sites/default/files/avis/2025-01/DO_AVIS_Avis_MCL_20243112_v3.1.pdf" class="card-link fs-lg-6 d-flex align-items-center text-primary">
												<span class="pe-2">
													<svg class="bi" width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
														<path d="M1 9.88889V15.2222C1 15.6937 1.21071 16.1459 1.58579 16.4793C1.96086 16.8127 2.46957 17 3 17H15C15.5304 17 16.0391 16.8127 16.4142 16.4793C16.7893 16.1459 17 15.6937 17 15.2222V9.88889M9 1V11.6667M9 11.6667L5.5 8.55556M9 11.6667L12.5 8.55556" stroke="currentcolor" stroke-width="1.5625" stroke-linecap="round" stroke-linejoin="round"></path>
													</svg>
												</span>
												<span class="mc-animate t-hover">Download</span>
											</a>
										</div>
									</div>
								</div>
							</div>
						</div>
											<div class="col-12 col-lg-4" style="opacity: 0.987;">
							<div class="avis-card position-relative mx-auto rounded-3 h-100 d-lg-flex flex-column">
								<div class="card-header px-5 border-bottom border-1">
									<p class="fs-6 text-primary ff-century-gothic">
										<span>Casablanca</span>
										<span class="text-secondary px-3">|</span>
										<span>06/01/2025</span>
									</p>
								</div>
								<div class="card-body px-5 py-4 d-flex flex-column h-100">
									<h5 class="avis-title fw-bold fs-6 ff-century-gothic">
										<a class="text-reset" target="_blank" href="https://www.maroclear.com/sites/default/files/avis/2025-01/DO_AVIS_Avis_MCL_20243112_v1.1.pdf">MAROCLEAR NOTICE N° 593/2024</a>
									</h5>
									<div class="mt-5">
										<p class="fw-light fs-6">ADMISSION SUBORDINATED BONDS CREDIT DU MAROC</p>
										<div class="download-avis position-lg-absolute z-2">
											<a target="_blank" href="https://www.maroclear.com/sites/default/files/avis/2025-01/DO_AVIS_Avis_MCL_20243112_v1.1.pdf" class="card-link fs-lg-6 d-flex align-items-center text-primary">
												<span class="pe-2">
													<svg class="bi" width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
														<path d="M1 9.88889V15.2222C1 15.6937 1.21071 16.1459 1.58579 16.4793C1.96086 16.8127 2.46957 17 3 17H15C15.5304 17 16.0391 16.8127 16.4142 16.4793C16.7893 16.1459 17 15.6937 17 15.2222V9.88889M9 1V11.6667M9 11.6667L5.5 8.55556M9 11.6667L12.5 8.55556" stroke="currentcolor" stroke-width="1.5625" stroke-linecap="round" stroke-linejoin="round"></path>
													</svg>
												</span>
												<span class="mc-animate t-hover">Download</span>
											</a>
										</div>
									</div>
								</div>
							</div>
						</div>
									<div class="col-12 col-lg-4" style="opacity: 0.987;">
							<div class="avis-card position-relative mx-auto rounded-3 h-100 d-lg-flex flex-column">
								<div class="card-header px-5 border-bottom border-1">
									<p class="fs-6 text-primary ff-century-gothic">
										<span>Casablanca</span>
										<span class="text-secondary px-3">|</span>
										<span>06/01/2025</span>
									</p>
								</div>
								<div class="card-body px-5 py-4 d-flex flex-column h-100">
									<h5 class="avis-title fw-bold fs-6 ff-century-gothic">
										<a class="text-reset" target="_blank" href="https://www.maroclear.com/sites/default/files/avis/2025-01/DO_AVIS_Avis_MCL_20243112_v2.1.pdf">MAROCLEAR NOTICE N° 593/2024</a>
									</h5>
									<div class="mt-5">
										<p class="fw-light fs-6">ADMISSION SUBORDINATED BONDS CREDIT AGRICOLE DU MAROC</p>
										<div class="download-avis position-lg-absolute z-2">
											<a target="_blank" href="https://www.maroclear.com/sites/default/files/avis/2025-01/DO_AVIS_Avis_MCL_20243112_v2.1.pdf" class="card-link fs-lg-6 d-flex align-items-center text-primary">
												<span class="pe-2">
													<svg class="bi" width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
														<path d="M1 9.88889V15.2222C1 15.6937 1.21071 16.1459 1.58579 16.4793C1.96086 16.8127 2.46957 17 3 17H15C15.5304 17 16.0391 16.8127 16.4142 16.4793C16.7893 16.1459 17 15.6937 17 15.2222V9.88889M9 1V11.6667M9 11.6667L5.5 8.55556M9 11.6667L12.5 8.55556" stroke="currentcolor" stroke-width="1.5625" stroke-linecap="round" stroke-linejoin="round"></path>
													</svg>
												</span>
												<span class="mc-animate t-hover">Download</span>
											</a>
										</div>
									</div>
								</div>
							</div>
						</div></div>
				<div class="swiper avis-list-section avis-swiper pb-7 mc-animate fade-in-up delay-items swiper-initialized swiper-horizontal swiper-backface-hidden" style="">
					
					<div class="swiper-wrapper" id="swiper-wrapper-88cb1243f9bc72c5" aria-live="polite" style="transition-duration: 0ms; transition-delay: 0ms; translate: none; rotate: none; scale: none; transform: translate3d(0px, 0px, 0px); opacity: 0;">
													<div class="swiper-slide swiper-slide-active" role="group" aria-label="1 / 3" style="width: 340.5px; margin-right: 25px;">
								<div class="avis-card position-relative mx-auto rounded-3 h-100 d-flex flex-column">
									<div class="card-header px-5 border-bottom border-1">
										<p class="fs-6 text-primary ff-century-gothic">
											<span>Casablanca</span>
											<span class="text-secondary px-3">|</span>
											<span>06/01/2025</span>
										</p>
									</div>
									<div class="card-body px-5 py-4 d-flex flex-column h-100">
										<h5 class="avis-title fw-bold fs-6 ff-century-gothic">
											<a class="text-reset" target="_blank" href="https://www.maroclear.com/sites/default/files/avis/2025-01/DO_AVIS_Avis_MCL_20243112_v3.1.pdf">MAROCLEAR NOTICE N° 594/2024</a>
										</h5>
										<div class="mt-5">
											<p class="fw-light fs-6"></p>
											<div class="download-avis position-lg-absolute z-2">
												<a href="https://www.maroclear.com/sites/default/files/avis/2025-01/DO_AVIS_Avis_MCL_20243112_v3.1.pdf" download="" class="card-link fs-lg-6 d-flex align-items-center text-primary">
													<span class="pe-2">
														<svg class="bi" width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
															<path d="M1 9.88889V15.2222C1 15.6937 1.21071 16.1459 1.58579 16.4793C1.96086 16.8127 2.46957 17 3 17H15C15.5304 17 16.0391 16.8127 16.4142 16.4793C16.7893 16.1459 17 15.6937 17 15.2222V9.88889M9 1V11.6667M9 11.6667L5.5 8.55556M9 11.6667L12.5 8.55556" stroke="currentcolor" stroke-width="1.5625" stroke-linecap="round" stroke-linejoin="round"></path>
														</svg>
													</span>
													<span class="mc-animate t-hover">Download</span>
												</a>
											</div>
										</div>
									</div>
								</div>
							</div>
													<div class="swiper-slide swiper-slide-next" role="group" aria-label="2 / 3" style="width: 340.5px; margin-right: 25px;">
								<div class="avis-card position-relative mx-auto rounded-3 h-100 d-flex flex-column">
									<div class="card-header px-5 border-bottom border-1">
										<p class="fs-6 text-primary ff-century-gothic">
											<span>Casablanca</span>
											<span class="text-secondary px-3">|</span>
											<span>06/01/2025</span>
										</p>
									</div>
									<div class="card-body px-5 py-4 d-flex flex-column h-100">
										<h5 class="avis-title fw-bold fs-6 ff-century-gothic">
											<a class="text-reset" target="_blank" href="https://www.maroclear.com/sites/default/files/avis/2025-01/DO_AVIS_Avis_MCL_20243112_v1.1.pdf">MAROCLEAR NOTICE N° 593/2024</a>
										</h5>
										<div class="mt-5">
											<p class="fw-light fs-6">ADMISSION SUBORDINATED BONDS CREDIT DU MAROC</p>
											<div class="download-avis position-lg-absolute z-2">
												<a href="https://www.maroclear.com/sites/default/files/avis/2025-01/DO_AVIS_Avis_MCL_20243112_v1.1.pdf" download="" class="card-link fs-lg-6 d-flex align-items-center text-primary">
													<span class="pe-2">
														<svg class="bi" width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
															<path d="M1 9.88889V15.2222C1 15.6937 1.21071 16.1459 1.58579 16.4793C1.96086 16.8127 2.46957 17 3 17H15C15.5304 17 16.0391 16.8127 16.4142 16.4793C16.7893 16.1459 17 15.6937 17 15.2222V9.88889M9 1V11.6667M9 11.6667L5.5 8.55556M9 11.6667L12.5 8.55556" stroke="currentcolor" stroke-width="1.5625" stroke-linecap="round" stroke-linejoin="round"></path>
														</svg>
													</span>
													<span class="mc-animate t-hover">Download</span>
												</a>
											</div>
										</div>
									</div>
								</div>
							</div>
													<div class="swiper-slide" role="group" aria-label="3 / 3" style="width: 340.5px; margin-right: 25px;">
								<div class="avis-card position-relative mx-auto rounded-3 h-100 d-flex flex-column">
									<div class="card-header px-5 border-bottom border-1">
										<p class="fs-6 text-primary ff-century-gothic">
											<span>Casablanca</span>
											<span class="text-secondary px-3">|</span>
											<span>06/01/2025</span>
										</p>
									</div>
									<div class="card-body px-5 py-4 d-flex flex-column h-100">
										<h5 class="avis-title fw-bold fs-6 ff-century-gothic">
											<a class="text-reset" target="_blank" href="https://www.maroclear.com/sites/default/files/avis/2025-01/DO_AVIS_Avis_MCL_20243112_v2.1.pdf">MAROCLEAR NOTICE N° 593/2024</a>
										</h5>
										<div class="mt-5">
											<p class="fw-light fs-6">ADMISSION SUBORDINATED BONDS CREDIT AGRICOLE DU MAROC</p>
											<div class="download-avis position-lg-absolute z-2">
												<a href="https://www.maroclear.com/sites/default/files/avis/2025-01/DO_AVIS_Avis_MCL_20243112_v2.1.pdf" download="" class="card-link fs-lg-6 d-flex align-items-center text-primary">
													<span class="pe-2">
														<svg class="bi" width="18" height="18" viewBox="0 0 18 18" fill="none" xmlns="http://www.w3.org/2000/svg">
															<path d="M1 9.88889V15.2222C1 15.6937 1.21071 16.1459 1.58579 16.4793C1.96086 16.8127 2.46957 17 3 17H15C15.5304 17 16.0391 16.8127 16.4142 16.4793C16.7893 16.1459 17 15.6937 17 15.2222V9.88889M9 1V11.6667M9 11.6667L5.5 8.55556M9 11.6667L12.5 8.55556" stroke="currentcolor" stroke-width="1.5625" stroke-linecap="round" stroke-linejoin="round"></path>
														</svg>
													</span>
													<span class="mc-animate t-hover">Download</span>
												</a>
											</div>
										</div>
									</div>
								</div>
							</div>
											</div>

				<div class="swiper-scrollbar swiper-scrollbar-horizontal" style="translate: none; rotate: none; scale: none; transform: translate(0px, 50px); opacity: 0;"><div class="swiper-scrollbar-drag" style="transition-duration: 0ms; transform: translate3d(0px, 0px, 0px); width: 91px;"></div></div><span class="swiper-notification" aria-live="assertive" aria-atomic="true" style="translate: none; rotate: none; scale: none; transform: translate(0px, 50px); opacity: 0;"></span></div>
				<div class="mt-7 text-center">
								<a style="" href="https://www.maroclear.com/en/cadre-reglementaire-legal?to=avis" class="d-lg-none w-100 text-center justify-content-center fs-lg-6 fw-medium btn btn-primary mc-animate t-primary icon-link">
		<span>View all reviews</span>
	</a>

				</div>
			</div>
		</div>
	</div>
	<div class="avis-bg position-absolute h-100 w-100 start-0 top-0 z-2">
		<div class="bg-top-left d-none d-lg-block position-absolute start-0 top-0">
			<img alt="avis-bg-img" loading="lazy" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/avis-background.svg">
		</div>
		<div class="bg-bottom-left d-none d-lg-block position-absolute start-0 bottom-0">
			<img alt="avis-bg-img" loading="lazy" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/avis-background-2.svg">
		</div>
		<div class="bg-top-right position-absolute end-0 top-0">
			<img alt="avis-bg-img" loading="lazy" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/avis-background-3.svg">
		</div>
		<div class="bg-bottom-mobile d-block d-lg-none position-absolute start-0 bottom-0 w-100">
			<img alt="avis-bg-img" loading="lazy" class="w-100" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/avis-bg-mobile.svg">
		</div>
	</div>
</section>
<!-- Avis et instructions- END -->

</div>

</div>
<!-- Présentation du Dépositaire Central - START -->

<section itemscope="" itemtype="https://schema.org/Article" id="block-maroclear-theme-presentationdudepositairecentral" class="presentation-depositaire mc-animate fade-on-scroll" style="translate: none; rotate: none; scale: none; transform: translate(0px, 100px); opacity: 0;">
	

	<meta itemprop="datePublished" content="2024-09-12">
	<meta itemprop="dateModified" content="2025-01-02">
	<meta itemprop="author" content="Maroclear">
	<meta itemprop="headline" content="Presentation of the Depository">
  	<meta itemprop="image" content="public://2024-09/G3A_CASA_VUE-03-HD_v6-Copie-e1596541731367-1_0_0.webp">
  	<meta itemprop="mainEntityOfPage " content="https://www.maroclear.com/en">

	 <!-- Publisher information (hidden) -->
	 <div itemprop="publisher" itemscope="" itemtype="https://schema.org/Organization">
		<meta itemprop="name" content="Maroclear">
		<meta itemprop="logo" content="logo.jpg">
	  </div>
	<div class="mc-container-fluid">
		<div class="row row-gap-5 align-items-center gx-0">
			<div class="col-12 col-lg-6 text-center pre-dep__img">
				<h2 class="d-block d-lg-none">
					Presentation of the Central Depository
				</h2>
				<div class="pre-dep__img-container">
					  <img loading="lazy" src="https://www.maroclear.com/sites/default/files/2024-09/G3A_CASA_VUE-03-HD_v6-Copie-e1596541731367-1_0_0.webp" width="652" height="657" alt="maroclear">


				</div>
			</div>
			<div class="col-12 col-lg-6 pre-dep__content pe-lg-0">
				<h2 class="d-none d-lg-block">
					Presentation of the Depository
				</h2>
				<div class="pre-dep-description text-justify fs-lg-6 fw-light" itemprop="articleBody">
					<p>Maroclear, Central Depositary, is responsible for the custody and settlement of transactions on financial instruments.<br>Infrastructure essential to the proper functioning of the capital market, it guarantees security and resilience in accordance with international standards.<br>&nbsp;</p>
				</div>

				<div class="row d-none d-lg-flex row-cols-1 row-cols-lg-2 row-gap-3 row-gap-lg-2 gx-0  pre-dep__links">
				
					
											<div class="col">
							<a href="https://www.maroclear.com/en/a-propos" class="btn btn-secondary btn-img-icon w-100 h-100 icon-link-hover mc-animate fade-in-up" style="translate: none; rotate: none; scale: none; transform: translate(0px, 50px); opacity: 0;">
								<span class="btn-img"><img src="https://www.maroclear.com/sites/default/files/2024-09/clarity_building-line.svg" loading="lazy" alt="icon"></span>
								<span class="btn-text-icon">
									<span>About us</span><img class="bi" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/arrow-right-green.svg" alt="green arrow right">
								</span>
							</a>
						</div>
											<div class="col">
							<a href="https://www.maroclear.com/en/gouvernance" class="btn btn-secondary btn-img-icon w-100 h-100 icon-link-hover mc-animate fade-in-up" style="translate: none; rotate: none; scale: none; transform: translate(0px, 50px); opacity: 0;">
								<span class="btn-img"><img src="https://www.maroclear.com/sites/default/files/2024-09/carbon_diagram-reference.svg" loading="lazy" alt="icon"></span>
								<span class="btn-text-icon">
									<span>Governance</span><img class="bi" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/arrow-right-green.svg" alt="green arrow right">
								</span>
							</a>
						</div>
											<div class="col">
							<a href="https://www.maroclear.com/en/capital-humain" class="btn btn-secondary btn-img-icon w-100 h-100 icon-link-hover mc-animate fade-in-up" style="translate: none; rotate: none; scale: none; transform: translate(0px, 50px); opacity: 0;">
								<span class="btn-img"><img src="https://www.maroclear.com/sites/default/files/2024-09/Vector.svg" loading="lazy" alt="icon"></span>
								<span class="btn-text-icon">
									<span>Human Capital</span><img class="bi" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/arrow-right-green.svg" alt="green arrow right">
								</span>
							</a>
						</div>
											<div class="col">
							<a href="https://www.maroclear.com/en/missions-valeurs" class="btn btn-secondary btn-img-icon w-100 h-100 icon-link-hover mc-animate fade-in-up" style="translate: none; rotate: none; scale: none; transform: translate(0px, 50px); opacity: 0;">
								<span class="btn-img"><img src="https://www.maroclear.com/sites/default/files/2024-09/carbon_web-services-container.svg" loading="lazy" alt="icon"></span>
								<span class="btn-text-icon">
									<span>Missions and values</span><img class="bi" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/arrow-right-green.svg" alt="green arrow right">
								</span>
							</a>
						</div>
											<div class="col">
							<a href="https://www.maroclear.com/en/cadre-reglementaire-legal" class="btn btn-secondary btn-img-icon w-100 h-100 icon-link-hover mc-animate fade-in-up" style="translate: none; rotate: none; scale: none; transform: translate(0px, 50px); opacity: 0;">
								<span class="btn-img"><img src="https://www.maroclear.com/sites/default/files/2024-09/fluent_document-search-32-regular.svg" loading="lazy" alt="icon"></span>
								<span class="btn-text-icon">
									<span>Regulatory and Legal Framework</span><img class="bi" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/arrow-right-green.svg" alt="green arrow right">
								</span>
							</a>
						</div>
											<div class="col">
							<a href="https://www.maroclear.com/en/vision-strategie" class="btn btn-secondary btn-img-icon w-100 h-100 icon-link-hover mc-animate fade-in-up" style="translate: none; rotate: none; scale: none; transform: translate(0px, 50px); opacity: 0;">
								<span class="btn-img"><img src="https://www.maroclear.com/sites/default/files/2024-09/Strat%C3%A9gie%20et%20vision.svg" loading="lazy" alt="icon"></span>
								<span class="btn-text-icon">
									<span>Vision and Strategy</span><img class="bi" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/arrow-right-green.svg" alt="green arrow right">
								</span>
							</a>
						</div>
					
				</div>
				<div class="swiper d-lg-none pre-depositaire-swiper pre-dep__links pb-7 swiper-initialized swiper-horizontal">
					<div class="swiper-wrapper" id="swiper-wrapper-c0b103226933a266a" aria-live="polite" style="transition-duration: 0ms; transition-delay: 0ms;">
													<div class="swiper-slide">
								
							<a href="https://www.maroclear.com/en/a-propos" class="btn btn-secondary btn-img-icon w-100 h-100 icon-link-hover mc-animate fade-in-up" style="opacity: 0.987;">
									<span class="btn-img position-relative">
										<img src="https://www.maroclear.com/sites/default/files/2024-09/clarity_building-line.svg" loading="lazy" alt="icon"></span>
										<div class="swiper-lazy-preloader swiper-lazy-preloader-white"></div>
									<span class="btn-text-icon">
								
										<span>About us</span><img class="bi" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/arrow-right-green.svg" alt="green arrow right">
									</span>
								</a></div>
													<div class="swiper-slide">
								
							<a href="https://www.maroclear.com/en/gouvernance" class="btn btn-secondary btn-img-icon w-100 h-100 icon-link-hover mc-animate fade-in-up" style="opacity: 0.987;">
									<span class="btn-img position-relative">
										<img src="https://www.maroclear.com/sites/default/files/2024-09/carbon_diagram-reference.svg" loading="lazy" alt="icon"></span>
										<div class="swiper-lazy-preloader swiper-lazy-preloader-white"></div>
									<span class="btn-text-icon">
								
										<span>Governance</span><img class="bi" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/arrow-right-green.svg" alt="green arrow right">
									</span>
								</a></div>
													<div class="swiper-slide">
								
							<a href="https://www.maroclear.com/en/capital-humain" class="btn btn-secondary btn-img-icon w-100 h-100 icon-link-hover mc-animate fade-in-up" style="opacity: 0.987;">
									<span class="btn-img position-relative">
										<img src="https://www.maroclear.com/sites/default/files/2024-09/Vector.svg" loading="lazy" alt="icon"></span>
										<div class="swiper-lazy-preloader swiper-lazy-preloader-white"></div>
									<span class="btn-text-icon">
								
										<span>Human Capital</span><img class="bi" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/arrow-right-green.svg" alt="green arrow right">
									</span>
								</a></div>
													<div class="swiper-slide">
								
							<a href="https://www.maroclear.com/en/missions-valeurs" class="btn btn-secondary btn-img-icon w-100 h-100 icon-link-hover mc-animate fade-in-up" style="opacity: 0.987;">
									<span class="btn-img position-relative">
										<img src="https://www.maroclear.com/sites/default/files/2024-09/carbon_web-services-container.svg" loading="lazy" alt="icon"></span>
										<div class="swiper-lazy-preloader swiper-lazy-preloader-white"></div>
									<span class="btn-text-icon">
								
										<span>Missions and values</span><img class="bi" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/arrow-right-green.svg" alt="green arrow right">
									</span>
								</a></div>
													<div class="swiper-slide">
								
							<a href="https://www.maroclear.com/en/cadre-reglementaire-legal" class="btn btn-secondary btn-img-icon w-100 h-100 icon-link-hover mc-animate fade-in-up" style="opacity: 0.987;">
									<span class="btn-img position-relative">
										<img src="https://www.maroclear.com/sites/default/files/2024-09/fluent_document-search-32-regular.svg" loading="lazy" alt="icon"></span>
										<div class="swiper-lazy-preloader swiper-lazy-preloader-white"></div>
									<span class="btn-text-icon">
								
										<span>Regulatory and Legal Framework</span><img class="bi" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/arrow-right-green.svg" alt="green arrow right">
									</span>
								</a></div>
													<div class="swiper-slide">
								
							<a href="https://www.maroclear.com/en/vision-strategie" class="btn btn-secondary btn-img-icon w-100 h-100 icon-link-hover mc-animate fade-in-up" style="opacity: 0.987;">
									<span class="btn-img position-relative">
										<img src="https://www.maroclear.com/sites/default/files/2024-09/Strat%C3%A9gie%20et%20vision.svg" loading="lazy" alt="icon"></span>
										<div class="swiper-lazy-preloader swiper-lazy-preloader-white"></div>
									<span class="btn-text-icon">
								
										<span>Vision and Strategy</span><img class="bi" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/arrow-right-green.svg" alt="green arrow right">
									</span>
								</a></div>
											</div>
					<div class="swiper-scrollbar swiper-scrollbar-horizontal"><div class="swiper-scrollbar-drag" style="width: 91px;"></div></div>

				<span class="swiper-notification" aria-live="assertive" aria-atomic="true"></span></div>
			</div>
		</div>
	</div>
</section>
<!-- Présentation du Dépositaire Central- END -->


<div class="fs-lg-6">
	<div><!-- Evénement et actualités - START -->
	<section class="js-view-dom-id-7a9f9b318cd89325333684e7fac28acdf613520a57584402951f714ddf12094f evenements py-8 bg-light mc-animate fade-on-scroll" data-once="ajax-pager" style="translate: none; rotate: none; scale: none; transform: translate(0px, 100px); opacity: 0;">
		
		

										<div class="mc-container-fluid pe-lg-0">
			<div class="row gx-0 row-gap-6">
									<div class="col-12 col-lg-4 pe-lg-8 d-flex justify-content-center align-items-center">

						<div class="evenements-decription text-center text-lg-start h-auto">
							<h2 class="mb-5">Events and news</h2>
							<div class="mb-4 fs-lg-6 text-justify">
								
							</div>
													<a style="max-width:314px;" href="https://www.maroclear.com/en/events" class="d-none d-lg-inline-flex w-100 text-center justify-content-center fs-lg-6 fw-medium btn btn-primary mc-animate t-primary icon-link">
			<span>Access all our news</span>
		</a>
	
						</div>
					</div>

														<div class="col-12 col-lg-8">
												<div class="evenements-cards-list">
							<!-- Swiper -->
							<div class="swiper events-swipper swiper-initialized swiper-horizontal swiper-backface-hidden">
								<div class="swiper-wrapper mc-animate fade-in-right delay-items" id="swiper-wrapper-f563a696e4aa6bd10" aria-live="polite" style="transform: translate3d(0px, 0px, 0px);">
																																																		<div class="swiper-slide swiper-slide-active" role="group" aria-label="1 / 5" style="translate: none; rotate: none; scale: none; transform: translate(1920px, 0px); opacity: 0; margin-right: 25px;">
												<a href="https://www.maroclear.com/en/actualites/ameda-doha-2024" class="actualite-card text-reset shadow processed" style="height: 405px;">
													<div class="card-img position-relative">
																																											
	  <picture>
                  <source srcset="/sites/default/files/styles/galerie_desktop/public/2024-12/AMEDA%20DOHA%20.jpeg.webp?itok=IP5ZfQcB 1x" media="all and (min-width: 992px)" type="image/webp" width="850" height="478">
              <source srcset="/sites/default/files/styles/galerie_mobile/public/2024-12/AMEDA%20DOHA%20.jpeg.webp?itok=PK95HcaB 1x" media="all and (min-width: 576px) and (max-width: 991px)" type="image/webp" width="650" height="366">
              <source srcset="/sites/default/files/styles/max_650x650/public/2024-12/AMEDA%20DOHA%20.jpeg.webp?itok=ekInnuyA 1x" media="all and (max-width: 577px)" type="image/webp" width="650" height="366">
                  <img loading="lazy" src="https://www.maroclear.com/sites/default/files/2024-12/AMEDA%20DOHA%20.jpeg" alt="text">

  </picture>


														
													</div>
													<div class="card-body">
														<div class="card-details">
															<div class="event-card-header pb-20 d-flex justify-content-between">
																<p class="mb-0 fs-6 fw-light">
																																	Events
																</p>
																<p class="mb-0 event-date fs-6 fw-light">
																	06/05/2024
																</p>
															</div>
															<p class="card-title fs-6 fw-bold">
																<span class="txt-deco-none text-dark">AMEDA DOHA 2024</span>
															</p>
																													</div>
														<div class="card-link">
															<span class="text-primary">
																<span class="fs-6 fw-light mc-animate t-hover">Read the article</span>
																<span class="ps-1">
																	<svg class="bi rotate-to-left" width="9" height="12" viewBox="0 0 9 12" fill="none" xmlns="http://www.w3.org/2000/svg">
																		<path fillRule="evenodd" clip-rule="evenodd" d="M1.72064 0L8.60449 6L1.72064 12L-0.000324249 10.5L5.16257 6L-0.000324249 1.5L1.72064 0Z" fill="currentcolor"></path>
																	</svg>
																</span>
															</span>
														</div>
													</div>
												</a>
											</div>

																																																												<div class="swiper-slide swiper-slide-next" role="group" aria-label="2 / 5" style="translate: none; rotate: none; scale: none; transform: translate(1920px, 0px); opacity: 0; margin-right: 25px;">
												<a href="https://www.maroclear.com/en/actualites/maroclears-participation-2024-edition-sibos-annual-conference-organized-swift-financial" class="actualite-card text-reset shadow processed" style="height: 405px;">
													<div class="card-img position-relative">
																																											
	  <picture>
                  <source srcset="/sites/default/files/styles/galerie_desktop/public/2024-11/sibos.png.webp?itok=xsBZdedH 1x" media="all and (min-width: 992px)" type="image/webp" width="850" height="504">
              <source srcset="/sites/default/files/styles/galerie_mobile/public/2024-11/sibos.png.webp?itok=rYnPFB3p 1x" media="all and (min-width: 576px) and (max-width: 991px)" type="image/webp" width="650" height="386">
              <source srcset="/sites/default/files/styles/max_650x650/public/2024-11/sibos.png.webp?itok=pH8mRVXu 1x" media="all and (max-width: 577px)" type="image/webp" width="650" height="386">
                  <img loading="lazy" src="https://www.maroclear.com/sites/default/files/2024-11/sibos.png" alt="Sibos">

  </picture>


														
													</div>
													<div class="card-body">
														<div class="card-details">
															<div class="event-card-header pb-20 d-flex justify-content-between">
																<p class="mb-0 fs-6 fw-light">
																																	Events
																</p>
																<p class="mb-0 event-date fs-6 fw-light">
																	21/10/2024
																</p>
															</div>
															<p class="card-title fs-6 fw-bold">
																<span class="txt-deco-none text-dark">Maroclear's participation in the 2024 edition of SIBOS, the annual conference organized by SWIFT for the financial industry.</span>
															</p>
																													</div>
														<div class="card-link">
															<span class="text-primary">
																<span class="fs-6 fw-light mc-animate t-hover">Read the article</span>
																<span class="ps-1">
																	<svg class="bi rotate-to-left" width="9" height="12" viewBox="0 0 9 12" fill="none" xmlns="http://www.w3.org/2000/svg">
																		<path fillRule="evenodd" clip-rule="evenodd" d="M1.72064 0L8.60449 6L1.72064 12L-0.000324249 10.5L5.16257 6L-0.000324249 1.5L1.72064 0Z" fill="currentcolor"></path>
																	</svg>
																</span>
															</span>
														</div>
													</div>
												</a>
											</div>

																																																												<div class="swiper-slide" role="group" aria-label="3 / 5" style="translate: none; rotate: none; scale: none; transform: translate(1920px, 0px); opacity: 0; margin-right: 25px;">
												<a href="https://www.maroclear.com/en/actualites/cross-border-resolution-transactions-settlementdelivery-blockchain" class="actualite-card text-reset shadow processed" style="height: 405px;">
													<div class="card-img position-relative">
																																											
	  <picture>
                  <source srcset="/sites/default/files/styles/galerie_desktop/public/2024-09/D%C3%A9nouement%20Transfrontalier.png.webp?itok=3tPVmxYk 1x" media="all and (min-width: 992px)" type="image/webp" width="850" height="1193">
              <source srcset="/sites/default/files/styles/galerie_mobile/public/2024-09/D%C3%A9nouement%20Transfrontalier.png.webp?itok=pnUOD3oK 1x" media="all and (min-width: 576px) and (max-width: 991px)" type="image/webp" width="650" height="912">
              <source srcset="/sites/default/files/styles/max_650x650/public/2024-09/D%C3%A9nouement%20Transfrontalier.png.webp?itok=NmFFdn8- 1x" media="all and (max-width: 577px)" type="image/webp" width="463" height="650">
                  <img loading="lazy" src="https://www.maroclear.com/sites/default/files/2024-09/D%C3%A9nouement%20Transfrontalier.png" alt="Worem ipsum dolor sit amet, consectetur adipiscing elit. Etiam eu turpis molestie, dictum est a, mattis tellus. Sed dignissim, metus nec fringilla accumsan, risus sem condimentum velit.  Worem ipsum dolor sit amet, consectetur adipiscing elit. Etiam eu turpis molestie, dictum est a, mattis tellus. Sed dignissim, metus nec fringilla accumsan, risus sem sollicitudin lacus, ut interdum tellus elit sed risus. Maecenas eget condimentum velit, sit amet feugiat lectus. Class aptent taciti sociosqu ad litora torque">

  </picture>


														
													</div>
													<div class="card-body">
														<div class="card-details">
															<div class="event-card-header pb-20 d-flex justify-content-between">
																<p class="mb-0 fs-6 fw-light">
																																	Events
																</p>
																<p class="mb-0 event-date fs-6 fw-light">
																	08/10/2019
																</p>
															</div>
															<p class="card-title fs-6 fw-bold">
																<span class="txt-deco-none text-dark">Cross-border resolution of transactions in Settlement/Delivery on the Blockchain</span>
															</p>
																													</div>
														<div class="card-link">
															<span class="text-primary">
																<span class="fs-6 fw-light mc-animate t-hover">Read the article</span>
																<span class="ps-1">
																	<svg class="bi rotate-to-left" width="9" height="12" viewBox="0 0 9 12" fill="none" xmlns="http://www.w3.org/2000/svg">
																		<path fillRule="evenodd" clip-rule="evenodd" d="M1.72064 0L8.60449 6L1.72064 12L-0.000324249 10.5L5.16257 6L-0.000324249 1.5L1.72064 0Z" fill="currentcolor"></path>
																	</svg>
																</span>
															</span>
														</div>
													</div>
												</a>
											</div>

																																																												<div class="swiper-slide" role="group" aria-label="4 / 5" style="translate: none; rotate: none; scale: none; transform: translate(1920px, 0px); opacity: 0; margin-right: 25px;">
												<a href="https://www.maroclear.com/en/actualites/renewal-iso-27001-certification" class="actualite-card text-reset shadow processed" style="height: 405px;">
													<div class="card-img position-relative">
																																											
	  <picture>
                  <source srcset="/sites/default/files/styles/galerie_desktop/public/2024-09/ISO%2027001.png.webp?itok=Q-amblbU 1x" media="all and (min-width: 992px)" type="image/webp" width="850" height="399">
              <source srcset="/sites/default/files/styles/galerie_mobile/public/2024-09/ISO%2027001.png.webp?itok=za0FLpEb 1x" media="all and (min-width: 576px) and (max-width: 991px)" type="image/webp" width="650" height="305">
              <source srcset="/sites/default/files/styles/max_650x650/public/2024-09/ISO%2027001.png.webp?itok=YIi0KDYy 1x" media="all and (max-width: 577px)" type="image/webp" width="650" height="305">
                  <img loading="lazy" src="https://www.maroclear.com/sites/default/files/2024-09/ISO%2027001.png" alt="Renouvellement de la certification ISO 27001">

  </picture>


														
													</div>
													<div class="card-body">
														<div class="card-details">
															<div class="event-card-header pb-20 d-flex justify-content-between">
																<p class="mb-0 fs-6 fw-light">
																																	Company
																</p>
																<p class="mb-0 event-date fs-6 fw-light">
																	05/02/2020
																</p>
															</div>
															<p class="card-title fs-6 fw-bold">
																<span class="txt-deco-none text-dark">Renewal of ISO 27001 certification</span>
															</p>
																													</div>
														<div class="card-link">
															<span class="text-primary">
																<span class="fs-6 fw-light mc-animate t-hover">Read the article</span>
																<span class="ps-1">
																	<svg class="bi rotate-to-left" width="9" height="12" viewBox="0 0 9 12" fill="none" xmlns="http://www.w3.org/2000/svg">
																		<path fillRule="evenodd" clip-rule="evenodd" d="M1.72064 0L8.60449 6L1.72064 12L-0.000324249 10.5L5.16257 6L-0.000324249 1.5L1.72064 0Z" fill="currentcolor"></path>
																	</svg>
																</span>
															</span>
														</div>
													</div>
												</a>
											</div>

																																																												<div class="swiper-slide" role="group" aria-label="5 / 5" style="translate: none; rotate: none; scale: none; transform: translate(1920px, 0px); opacity: 0; margin-right: 25px;">
												<a href="https://www.maroclear.com/en/actualites/maroclear-fully-engaged-national-mobilization-0" class="actualite-card text-reset shadow processed" style="height: 405px;">
													<div class="card-img position-relative">
																																											
	  <picture>
                  <source srcset="/sites/default/files/styles/galerie_desktop/public/2024-09/Dons%20Covid.png.webp?itok=mzmF-Bho 1x" media="all and (min-width: 992px)" type="image/webp" width="850" height="737">
              <source srcset="/sites/default/files/styles/galerie_mobile/public/2024-09/Dons%20Covid.png.webp?itok=Wh0L3X9X 1x" media="all and (min-width: 576px) and (max-width: 991px)" type="image/webp" width="650" height="563">
              <source srcset="/sites/default/files/styles/max_650x650/public/2024-09/Dons%20Covid.png.webp?itok=0FFr3TaX 1x" media="all and (max-width: 577px)" type="image/webp" width="650" height="563">
                  <img loading="lazy" src="https://www.maroclear.com/sites/default/files/2024-09/Dons%20Covid.png" alt="MAROCLEAR pleinement engagé dans la mobilisation nationale">

  </picture>


														
													</div>
													<div class="card-body">
														<div class="card-details">
															<div class="event-card-header pb-20 d-flex justify-content-between">
																<p class="mb-0 fs-6 fw-light">
																																	Company
																</p>
																<p class="mb-0 event-date fs-6 fw-light">
																	26/03/2020
																</p>
															</div>
															<p class="card-title fs-6 fw-bold">
																<span class="txt-deco-none text-dark">MAROCLEAR fully engaged in national mobilization</span>
															</p>
																													</div>
														<div class="card-link">
															<span class="text-primary">
																<span class="fs-6 fw-light mc-animate t-hover">Read the article</span>
																<span class="ps-1">
																	<svg class="bi rotate-to-left" width="9" height="12" viewBox="0 0 9 12" fill="none" xmlns="http://www.w3.org/2000/svg">
																		<path fillRule="evenodd" clip-rule="evenodd" d="M1.72064 0L8.60449 6L1.72064 12L-0.000324249 10.5L5.16257 6L-0.000324249 1.5L1.72064 0Z" fill="currentcolor"></path>
																	</svg>
																</span>
															</span>
														</div>
													</div>
												</a>
											</div>

																											</div>
								<div class="swiper-scrollbar swiper-scrollbar-horizontal"><div class="swiper-scrollbar-drag" style="transform: translate3d(0px, 0px, 0px); width: 344px;"></div></div>
							<span class="swiper-notification" aria-live="assertive" aria-atomic="true"></span></div>
						</div>
					</div>
				</div>
									<div class="row justify-content-center mt-6">
						<div class="col col-md-8">
													<a style="" href="https://www.maroclear.com/en/events" class="d-lg-none w-100 text-center justify-content-center fs-lg-6 fw-medium btn btn-primary mc-animate t-primary icon-link">
			<span>Access all our news</span>
		</a>
	
						</div>

					</div>
							</div>
		</section>
		<!-- Evénement et actualités- END -->

	
	</div>

</div>
<!-- Réglementation - START -->

<section id="block-maroclear-theme-reglementation" class="reglementation py-8 mc-animate fade-on-scroll" style="translate: none; rotate: none; scale: none; transform: translate(0px, 100px); opacity: 0;">

	<div class="mc-container-fluid">
		<div class="row gx-6 gy-10 gy-lg-0">
			<div class="col-12 col-lg-5 text-center text-lg-start">
				<h2 class="mb-5 mb-lg-7 mt-lg-6 mt-0">
            <div>Regulation</div>
      </h2>
				<div class="fs-lg-6 fw-light text-justify">
					
            <div><p>Collection of regulatory texts applicable to the activities of central depositories.</p></div>
      
				</div>
			</div>
			<div class="col-12 col-lg-7">
				<div class="reglementation-swiper rounded-4">
					<div class="swiper regle-swipper swiper-coverflow swiper-3d swiper-initialized swiper-horizontal swiper-watch-progress">
						<div class="swiper-wrapper mb-8" id="swiper-wrapper-58bfaf2dc8237ba9" aria-live="polite" style="transition-duration: 0ms; transition-delay: 0ms; transform: translate3d(-221px, 0px, 0px);">
															<div class="swiper-slide swiper-slide-visible swiper-slide-prev" role="group" aria-label="1 / 4" style="transition-duration: 0ms; transform: translate3d(0px, 0px, -400px) rotateX(0deg) rotateY(0deg) scale(1); z-index: 0;">
									<div class="text-center">
										<div class="mb-6">
											<img src="https://www.maroclear.com/sites/default/files/2024-09/regl-2.svg" alt="reglementation-icon" loading="lazy">
										</div>

										<h4 class="mb-5 fs-5">Règles de fonctionnement
										</h4>
										<div class="mb-4 mb-lg-6 fs-lg-6 fw-light">
											<p>Les Règles de fonctionnement Maroclear ont pour finalité de détailler les règles de gestion fonctionnelles que doivent respecter les affiliés dans le traitement quotidien de leurs opérations avec MAROCLEAR dans ses systèmes.</p>
										</div>
										<a href="https://www.maroclear.com/en/cadre-reglementaire-legal?to=regles-de-fonctionnement" class="btn-link icon-link-hover fs-lg-6 fw-light mc-animate t-hover text-primary">Learn more</a><span class="ps-2 text-primary"><svg class="bi rotate-to-left" width="8" height="12" viewBox="0 0 8 12" fill="none" xmlns="http://www.w3.org/2000/svg">
										
												<path fillRule="evenodd" clip-rule="evenodd" d="M1.5 0L7.5 6L1.5 12L0 10.5L4.5 6L0 1.5L1.5 0Z" fill="currentcolor"></path>
											</svg></span>
										
																			</div>
								</div>
															<div class="swiper-slide swiper-slide-visible swiper-slide-fully-visible swiper-slide-active" role="group" aria-label="2 / 4" style="transition-duration: 0ms; transform: translate3d(0px, 0px, 0px) rotateX(0deg) rotateY(0deg) scale(1); z-index: 1;">
									<div class="text-center">
										<div class="mb-6">
											<img src="https://www.maroclear.com/sites/default/files/2024-09/lois.svg" alt="reglementation-icon" loading="lazy">
										</div>

										<h4 class="mb-5 fs-5">Lois
										</h4>
										<div class="mb-4 mb-lg-6 fs-lg-6 fw-light">
											<p>Fondé en 1997 sous forme de Société Anonyme en tant que Dépositaire Central des valeurs mobilières, en vertu des dispositions du Dahir n° 1-96-246 du 9 janvier 1997, portant promulgation de la loi n°35-96 relative notamment, à la création d’un dépositaire central ...</p>
										</div>
										<a href="https://www.maroclear.com/en/cadre-reglementaire-legal?to=lois" class="btn-link icon-link-hover fs-lg-6 fw-light mc-animate t-hover text-primary">Learn more</a><span class="ps-2 text-primary"><svg class="bi rotate-to-left" width="8" height="12" viewBox="0 0 8 12" fill="none" xmlns="http://www.w3.org/2000/svg">
										
												<path fillRule="evenodd" clip-rule="evenodd" d="M1.5 0L7.5 6L1.5 12L0 10.5L4.5 6L0 1.5L1.5 0Z" fill="currentcolor"></path>
											</svg></span>
										
																			</div>
								</div>
															<div class="swiper-slide swiper-slide-visible swiper-slide-next" role="group" aria-label="3 / 4" style="transition-duration: 0ms; transform: translate3d(0px, 0px, -400px) rotateX(0deg) rotateY(0deg) scale(1); z-index: 0;">
									<div class="text-center">
										<div class="mb-6">
											<img src="https://www.maroclear.com/sites/default/files/2024-09/carbon_information.svg" alt="reglementation-icon" loading="lazy">
										</div>

										<h4 class="mb-5 fs-5">Principes et directives
										</h4>
										<div class="mb-4 mb-lg-6 fs-lg-6 fw-light">
											<p>Le Dépositaire Central est régit par un ensemble de cadres internationaux et nationaux visant à garantir sa robustesse, sa transprance et sa résilience.</p>
										</div>
										<a href="https://www.maroclear.com/en/cadre-reglementaire-legal?to=cadre-info-pfmi" class="btn-link icon-link-hover fs-lg-6 fw-light mc-animate t-hover text-primary">Learn more</a><span class="ps-2 text-primary"><svg class="bi rotate-to-left" width="8" height="12" viewBox="0 0 8 12" fill="none" xmlns="http://www.w3.org/2000/svg">
										
												<path fillRule="evenodd" clip-rule="evenodd" d="M1.5 0L7.5 6L1.5 12L0 10.5L4.5 6L0 1.5L1.5 0Z" fill="currentcolor"></path>
											</svg></span>
										
																			</div>
								</div>
															<div class="swiper-slide" role="group" aria-label="4 / 4" style="transition-duration: 0ms; transform: translate3d(0px, 0px, -800px) rotateX(0deg) rotateY(0deg) scale(1); z-index: -1;">
									<div class="text-center">
										<div class="mb-6">
											<img src="https://www.maroclear.com/sites/default/files/2024-09/paper.svg" alt="reglementation-icon" loading="lazy">
										</div>

										<h4 class="mb-5 fs-5">Réglementation
										</h4>
										<div class="mb-4 mb-lg-6 fs-lg-6 fw-light">
											<p>La réglementation encadrant les activités de MAROCLEAR repose sur un ensemble de textes législatifs et réglementaires nationaux et internationaux.</p>
										</div>
										<a href="https://www.maroclear.com/en/cadre-reglementaire-legal?to=reglementation" class="btn-link icon-link-hover fs-lg-6 fw-light mc-animate t-hover text-primary">Learn more</a><span class="ps-2 text-primary"><svg class="bi rotate-to-left" width="8" height="12" viewBox="0 0 8 12" fill="none" xmlns="http://www.w3.org/2000/svg">
										
												<path fillRule="evenodd" clip-rule="evenodd" d="M1.5 0L7.5 6L1.5 12L0 10.5L4.5 6L0 1.5L1.5 0Z" fill="currentcolor"></path>
											</svg></span>
										
																			</div>
								</div>
							
						</div>
						<div class="swiper-pagination reglementation-swiper-pagination swiper-pagination-bullets swiper-pagination-horizontal"><span class="swiper-pagination-bullet"></span><span class="swiper-pagination-bullet swiper-pagination-bullet-active" aria-current="true"></span><span class="swiper-pagination-bullet"></span><span class="swiper-pagination-bullet"></span></div>
					<span class="swiper-notification" aria-live="assertive" aria-atomic="true"></span></div>
				</div>
			</div>
		</div>
	</div>
</section>
<!-- Réglementation- END -->



<footer aria-label="Site footer" class="footer " id="footer" role="contentinfo">
	<div class="footer bg-light pt-6 pt-lg-9 mc-container-fluid text-white">
		<div class="footer__container bg-dark ">
			<div class="row row-gap-9 align-items-center align-items-lg-start justify-content-center text-center text-lg-start">
				<div class="col-6 col-lg-3 ps-0">
					<div class="footer-slug mx-auto mx-lg-0">
						<img class="mb-4" src="https://www.maroclear.com/sites/default/files/theme/logo-white.svg" loading="lazy" alt="Maroclear">
						<p class="fs-5 fs-lg-4 fw-bolder" style="font-size: 28px">BUILDING TRUST</p>
					</div>
				</div>
				<div class="col-12 col-lg-6 row row-gap-9">
					<div class="col-12 col-lg-6">
					<p class="fs-lg-5 text-primary fw-medium mb-4">Activity</p>

						<nav role="navigation" aria-labelledby="block-maroclear-theme-footer-menu" id="block-maroclear-theme-footer">
            
  <h2 class="visually-hidden" id="block-maroclear-theme-footer-menu">Footer</h2>
  

        
<ul class="fs-lg-6 fw-light list-style-none d-flex flex-column row-gap-3 p-0 m-0">
			<li>
			<a class="txt-deco-none text-white mc-animate t-hover" href="https://www.maroclear.com/en/data-services/repository">Activity figures</a>
		</li>
			<li>
			<a class="txt-deco-none text-white mc-animate t-hover" href="https://www.maroclear.com/en/events">Events &amp; News</a>
		</li>
			<li>
			<a class="txt-deco-none text-white mc-animate t-hover" href="https://www.maroclear.com/en/partenaires">Partners</a>
		</li>
			<li>
			<a class="txt-deco-none text-white mc-animate t-hover" href="https://www.maroclear.com/en/glossaire">Glossary</a>
		</li>
	</ul>


  </nav>



					</div>
					<div class="col-12 col-lg-6">
					<p class="fs-lg-5 text-primary fw-medium mb-4">Maroclear</p>

						<nav role="navigation" aria-labelledby="block-maroclear-theme-footer2-menu" id="block-maroclear-theme-footer2">
            
  <h2 class="visually-hidden" id="block-maroclear-theme-footer2-menu">Footer 2</h2>
  

        
<ul class="fs-lg-6 fw-light list-style-none d-flex flex-column row-gap-3 p-0 m-0">
			<li>
			<a class="txt-deco-none text-white mc-animate t-hover" href="https://www.maroclear.com/a-propos">About us</a>
		</li>
			<li>
			<a class="txt-deco-none text-white mc-animate t-hover" href="https://www.maroclear.com/en/capital-humain?to=profils-pourvoir">Join us</a>
		</li>
			<li>
			<a class="txt-deco-none text-white mc-animate t-hover" href="https://www.maroclear.com/en/contact">Contact us</a>
		</li>
			<li>
			<a class="txt-deco-none text-white mc-animate t-hover" href="https://www.maroclear.com/en/certifications-labels">Certifications and labels</a>
		</li>
	</ul>


  </nav>

</div>
				</div>
				<div class="col-12 col-lg-3 pe-0">
					<h4 class="text-primary fs-5 mb-3 fw-medium">Follow us</h4>
					<div class="social-media d-flex justify-content-center justify-content-lg-start mb-9">
						
	<a href="https://www.facebook.com/p/Maroclear-100063506682731/?locale=fr_FR&amp;_rdr" target="_blank" id="facebook" title="Facebook" style="height: 30px;">
		<svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
			<g clip-path="url(#clip0_1_2)">
			<path d="M28 14.0852C28 6.35367 21.7315 0.0851669 14 0.0851669C6.2685 0.0851669 0 6.35367 0 14.0852C0 21.0735 5.11933 26.8648 11.8125 27.9148V18.1323H8.25767V14.0852H11.8125V11.0017C11.8125 7.4935 13.9032 5.55567 17.101 5.55567C18.6317 5.55567 20.2347 5.82867 20.2347 5.82867V9.27383H18.4695C16.73 9.27383 16.1875 10.353 16.1875 11.4613V14.0863H20.0702L19.4495 18.1347H16.1875V27.916C22.8807 26.8648 28 21.0735 28 14.0852Z" fill="white"></path>
			</g>
			<defs>
			<clipPath id="clip0_1_2">
			<rect width="28" height="28" fill="white"></rect>
			</clipPath>
			</defs>
		</svg>
	</a>
	<a href="https://x.com/maroclear_csd" target="_blank" id="twitter" title="X">
		<svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
			<g clip-path="url(#clip0_1_5)">
				<path d="M22.0512 1.16667H26.3445L16.9645 12.0388L28 26.8333H19.3597L12.593 17.8617L4.8475 26.8333H0.553L10.5863 15.204L0 1.16667H8.85967L14.9765 9.36833L22.0512 1.16667ZM20.545 24.227H22.9238L7.567 3.63533H5.01433L20.545 24.227Z" fill="white" stroke="white"></path>
			</g>
			<defs>
				<clipPath id="clip0_1_5">
					<rect width="28" height="28" fill="white"></rect>
				</clipPath>
			</defs>
		</svg>
	</a>

	<a href="https://www.linkedin.com/company/maroclear/" target="_blank" id="linkedin" title="Linkedin">
		<svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
		<g clip-path="url(#clip0_1_8)">
		<path d="M25.9268 0H2.06733C0.924 0 0 0.901833 0 2.01833V25.977C0 27.0923 0.924 28 2.06733 28H25.9268C27.0702 28 28 27.0923 28 25.9817V2.01833C28 0.901833 27.0702 0 25.9268 0ZM8.30667 23.8607H4.151V10.4942H8.30667V23.8607ZM6.23 8.673C5.90629 8.68535 5.58341 8.63225 5.28069 8.51689C4.97798 8.40153 4.70166 8.22627 4.46827 8.00161C4.23487 7.77695 4.04921 7.50751 3.92239 7.20941C3.79558 6.91132 3.73021 6.5907 3.73021 6.26675C3.73021 5.9428 3.79558 5.62218 3.92239 5.32409C4.04921 5.02599 4.23487 4.75655 4.46827 4.53189C4.70166 4.30723 4.97798 4.13197 5.28069 4.01661C5.58341 3.90125 5.90629 3.84815 6.23 3.8605C6.859 3.87435 7.45758 4.13395 7.89753 4.5837C8.33749 5.03345 8.58385 5.63759 8.58385 6.26675C8.58385 6.89591 8.33749 7.50005 7.89753 7.9498C7.45758 8.39955 6.859 8.65915 6.23 8.673ZM23.8607 23.8607H19.7097V17.3623C19.7097 15.8153 19.6817 13.8192 17.549 13.8192C15.3895 13.8192 15.0605 15.5097 15.0605 17.2538V23.8607H10.9153V10.4942H14.8972V12.3212H14.952C15.5038 11.2712 16.8607 10.1605 18.8778 10.1605C23.0837 10.1605 23.8595 12.9278 23.8595 16.527L23.8607 23.8607Z" fill="white" stroke="white"></path>
		</g>
		<defs>
		<clipPath id="clip0_1_8">
		<rect width="28" height="28" rx="2" fill="white"></rect>
		</clipPath>
		</defs>
		</svg>
	</a>
	<a href="https://www.youtube.com/@maroclear9487" target="_blank" id="youtube" title="Youtube">
		<svg width="39" height="28" viewBox="0 0 39 28" fill="none" xmlns="http://www.w3.org/2000/svg">
		<g clip-path="url(#clip0_1_11)">
		<path d="M38.61 6.1649C38.61 6.1649 38.2314 3.46173 37.0581 2.2743C35.5729 0.71283 33.9121 0.706297 33.15 0.613197C27.6965 0.216297 19.5081 0.216297 19.5081 0.216297H19.4919C19.4919 0.216297 11.3035 0.216297 5.85 0.613197C5.08787 0.706297 3.42875 0.71283 1.94188 2.2743C0.768625 3.46173 0.3965 6.1649 0.3965 6.1649C0.3965 6.1649 0 9.34173 0 12.512V15.4814C0 18.6517 0.39 21.8286 0.39 21.8286C0.39 21.8286 0.768625 24.5317 1.93375 25.7192C3.42063 27.2806 5.37062 27.2267 6.24 27.395C9.36 27.6939 19.5 27.787 19.5 27.787C19.5 27.787 27.6965 27.7706 33.15 27.3786C33.9121 27.2888 35.5713 27.2806 37.0581 25.7192C38.2314 24.5317 38.6116 21.8286 38.6116 21.8286C38.6116 21.8286 39 18.6599 39 15.4814V12.5137C39 9.34336 38.61 6.1649 38.61 6.1649ZM15.47 19.0878V8.071L26.0049 13.5982L15.47 19.0878Z" fill="white"></path>
		</g>
		<defs>
		<clipPath id="clip0_1_11">
		<rect width="39" height="28" fill="white"></rect>
		</clipPath>
		</defs>
		</svg>

	</a>

					</div>
					
				</div>
			</div>
		</div>

	</div>
			<div class="footer__bottom bg-light mc-container-fluid">
			<div class="row row-gap-2 align-items-center justify-content-center justify-content-lg-between py-6 pt-lg-4">
				<div class="col-auto menu-bottom">
					<div class="nav-top-left nav-top-left--orange">	<nav role="navigation" aria-labelledby="block-maroclear-theme-footerbottomlinks-menu" id="block-maroclear-theme-footerbottomlinks">
            
  <h2 class="visually-hidden" id="block-maroclear-theme-footerbottomlinks-menu">Footer Bottom links</h2>
  

        


											<ul class="nav-top-left__links row fw-light gx-6 mb-0 p-0 list-style-none">
									<li class="col-auto">
						<a class="txt-deco-none text-white mc-animate t-hover" href="https://www.maroclear.com/en/mentions-legales">Legal Notices</a>
					</li>
									<li class="col-auto">
						<a class="txt-deco-none text-white mc-animate t-hover" href="https://www.maroclear.com/en/sitemap">Sitemap</a>
					</li>
									<li class="col-auto">
						<a class="txt-deco-none text-white mc-animate t-hover" href="https://www.maroclear.com/en/politique-de-cookies">Policy of cookies</a>
					</li>
							</ul>
			

	

  </nav>

</div>
				</div>
				<div class="col-auto">
					<p class="m-0 copyright-text fs-lg-6 fw-light">
						2026.
						All rights reserved.
					</p>
				</div>
			</div>
		</div>
</footer>
<div class="menu-overlay-bg d-none position-fixed start-0 top-0 h-100 w-100 z-3" style="background-color: #30364563"></div>
	<div class="sticky-buttons d-none d-lg-flex flex-column align-items-end">
					<a class="sticky-buttons-item mc-animate t-all" href="https://www.maroclear.com/en/contact" title="">
				<img class="sticky-buttons-icon" alt="Contact us" src="https://www.maroclear.com/sites/default/files/2024-10/contact-us.svg">
        
				<span class="sticky-buttons-text mc-animate t-hover">Contact us</span>
			</a>

					<a class="sticky-buttons-item mc-animate t-all" href="https://www.maroclear.com/en/capital-humain?to=profils-pourvoir" title="">
				<img class="sticky-buttons-icon" alt="Join us" src="https://www.maroclear.com/sites/default/files/2024-10/join-us.svg">
        
				<span class="sticky-buttons-text mc-animate t-hover">Join us</span>
			</a>

					<a class="sticky-buttons-item mc-animate t-all" href="https://www.maroclear.com/en/events" title="">
				<img class="sticky-buttons-icon" alt="News" src="https://www.maroclear.com/sites/default/files/2024-10/news-light_0.svg">
        
				<span class="sticky-buttons-text mc-animate t-hover">News</span>

			</a>
            <a class="sticky-buttons-item mc-animate t-all" href="#" id="clearbot-trigger" onclick="document.getElementById('clearbot-open').click(); return false;">
<svg class="sticky-buttons-icon" width="41" height="41" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2v10z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="8" cy="10" r="1" fill="white"/>
  <circle cx="12" cy="10" r="1" fill="white"/>
  <circle cx="16" cy="10" r="1" fill="white"/>
</svg>
			<span class="sticky-buttons-text mc-animate t-hover">Assistant IA</span>
		</a>
		

		<a class="sticky-buttons-item mc-animate t-all" href="#" id="back-to-top">
			<img class="sticky-buttons-icon" alt="arrows top" src="https://www.maroclear.com/themes/custom/maroclear_theme/assets/images/icons/up.svg">
			<span class="sticky-buttons-text mc-animate t-hover">Go back to the top</span>
		</a>
	</div>



  </div>

    
    



  <iframe height="1" width="1" style="position: absolute; top: 0px; left: 0px; border: none; visibility: hidden;"></iframe>

<div id="drupal-live-announce" class="visually-hidden" aria-live="polite" aria-busy="false"></div>
  `;

  return (
	<>
	  {/* On imite les classes exactes du site Maroclear */}
	  <div className="path-frontpage node--type-page lang-en"> 
		<div className="dialog-off-canvas-main-canvas">
		  <main role="main">
			{/* Le contenu du site */}
			<div dangerouslySetInnerHTML={{ __html: siteHTML }} />
			
			{/* --- AGENT IA MAROCLEAR --- */}
			<MaroclearWidget />
		  </main>
		</div>
	  </div>
	</>
  );
}

export default App
