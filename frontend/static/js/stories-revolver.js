let currentIndex = 0;
const stories = document.querySelectorAll('#stories-container img');
const progressBars = document.querySelectorAll('.progress-fill');
const mySet = new Set();

document.querySelectorAll('#stories-container .cursor-pointer').forEach((img, index) => {
        img.addEventListener('click', () => {
                currentIndex = index;
                const modal = document.getElementById('stories-modal');
                modal.querySelector('img').src = img.src.replace('backgrounds thumb-', '').replace('.jpg', '-big.jpg');
        
                changeStoriesBorders(currentIndex);
                updateProgressBars(currentIndex);
                mySet.add(currentIndex);
        });
});

function storiesRevolver() {

        function showNextStory() {
                if (mySet.has(currentIndex)) currentIndex++;
                if (currentIndex >= stories.length) currentIndex = 0;
                
                stories[currentIndex].click();
                currentIndex = (currentIndex + 1) % stories.length;
                mySet.clear();
        }
        setInterval(showNextStory, 9000);
}

function updateProgressBars(currentIndex) {
        progressBars.forEach((bar, index) => {
                bar.style.transition = 'none';
                bar.style.width = '0%';
                bar.offsetHeight;

                bar.style.transition = '';
                index === currentIndex ? bar.style.width = '100%' : ''; 
        });
}

function changeStoriesBorders(currentIndex) {
        stories.forEach((story, index) => {
                story.classList.remove('ring-2', 'ring-heliotrope', 'border', 'border-white');

                index === currentIndex ? story.classList.add('ring-2', 'ring-heliotrope', 'border', 'border-white') : '';
        });
}

storiesRevolver();