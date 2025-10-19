let pc = null;
let localStream = null;

async function startVideoCall(otherUserId) {
    try {
        const localVideo = document.getElementById('local-video');
        const remoteVideo = document.getElementById('remote-video');

        localStream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: true
        });
        localVideo.srcObject = localStream;

        pc = new RTCPeerConnection({
            iceServers: [{ urls: 'stun:stun.1.google.com:19302' }]
        });

        localStream.getTracks().forEach(track => {
            pc.addTrack(track, localStream);
        });

        pc.ontrack = (event) => {
            remoteVideo.srcObject = event.streams[0];
        };

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        pc.onicecandidate = (event) => {
            if (event.candidate) {
                chatSocket.send(JSON.stringify({
                    type: 'ice_candidate',
                    candidate: event.candidate,
                    sender_id: userId
                }));
            }
        };

        chatSocket.send(JSON.stringify({
            type: 'video_call_offer',
            sender_id: userId,
            offer: offer
        }));
    } catch (error) {
        console.error('Error starting video call: ', error);
        alert('Camera access denied or not available');
    }
}

async function answerCall(offer, fromUserId) {
    try {
        if (!pc) {
            pc = new RTCPeerConnection({
                iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
            });

            localStream = await navigator.mediaDevices.getUserMedia({
                video: true,
                audio: true
            });
            document.getElementById('local-video').srcObject = localStream;

            localStream.getTracks().forEach(track => {
                pc.addTrack(track, localStream);
            });

            pc.ontrack = (event) => {
                document.getElementById('remote-video').srcObject = event.streams[0];
            };
        }

        await pc.setRemoteDescription(offer);

        if (window.queuedCandidates) {
            for (const candidate of window.queuedCandidates) {
                await pc.addIceCandidate(candidate);
            }
            window.queuedCandidates = [];
        }

        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);

        pc.onicecandidate = (event) => {
            if (event.candidate) {
                chatSocket.send(JSON.stringify({
                    type: 'ice_candidate',
                    candidate: event.candidate,
                    sender_id: userId
                }));
            }
        };

        chatSocket.send(JSON.stringify({
            type: 'video_call_answer',
            answer: answer,
            sender_id: userId,
            receiver_id: fromUserId
        }));
    } catch (error) {
        if (error.name === 'NotReadableError') {
            alert('Camera or microphone is already in use.');
        }
    }
}

async function handleCallAnswer(answer) {
    try {
        if (pc && pc.signalingState === 'have-local-offer') {
            await pc.setRemoteDescription(answer);
            console.log('Call answer processed');

        if (window.queuedCandidates) {
            for (const candidate of window.queuedCandidates) {
                await pc.addIceCandidate(candidate);
            }
            window.queuedCandidates = [];
        } 
    } else {
            console.log('Ignoring answer - wrong signaling state:', pc?.signalingState);
        }
    } catch (error) {
        console.error('Error handling call answer:', error);
    }
}