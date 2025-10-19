let mediaRecorder;
let audioChunks = [];
let currentStream;

document.querySelector('.audio-record-btn').addEventListener('click', async () => {
    if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        currentStream = await navigator.mediaDevices.getUserMedia({ audio: true});
        mediaRecorder = new MediaRecorder(currentStream);

        mediaRecorder.ondataavailable = event => audioChunks.push(event.data);

        mediaRecorder.onstop = () => {
            console.log('Recording stopped');

            document.querySelector('.audio-record-btn').classList.remove('recording');
            document.querySelector('.recording-indicator').style.display = 'none';
            
            currentStream.getTracks().forEach(track => track.stop());

            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            uploadAudio(audioBlob);

            audioChunks = [];
        };

        mediaRecorder.onstart = () => {
            console.log('Recording started');

            document.querySelector('.audio-record-btn').classList.add('recording');
            document.querySelector('.recording-indicator').style.display = 'block';
        };

        mediaRecorder.start();
    } else {
        mediaRecorder.stop();
    }
});
