import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: root
    width: 1440; height: 900; minimumWidth: 1080; minimumHeight: 700
    visible: true; color: "#030712"; title: "JARVIS — Gate 2B Visual Concept"
    property color ink: "#e1efff"; property color muted: "#8092b5"
    property color cyan: "#80ddff"; property color edge: "#25466c"
    property var bridge: typeof runtimeBridge === "undefined" ? null : runtimeBridge
    property string liveCoreState: bridge ? bridge.coreState : motion.coreState
    property int liveMissionStage: bridge ? bridge.missionStage : motion.missionStage
    // Development-only controller. It is isolated in QML and has no production
    // runtime, authorization, voice, agent, filesystem, or workflow binding.
    QtObject {
        id: motion
        objectName: "motionPrototypeController"
        property string coreState: "IDLE"
        property string scenario: "IDLE"
        property bool reducedMotion: false
        property real clock: 0
        property int phase: 0
        property int missionStage: 0
        property string researchState: "DORMANT"
        property string citationState: "DORMANT"
        property string writerState: "DORMANT"
        property string reviewerState: "DORMANT"
        property string builderState: "DORMANT"
        property string transferFrom: ""
        property string transferTo: ""
        property real transferProgress: 0
        property bool transferActive: false
        property string statusLine: "CALM / SYSTEM HEALTHY"
        function reset() {
            coreState="IDLE"; phase=0; missionStage=0; transferActive=false; transferProgress=0
            researchState="DORMANT"; citationState="DORMANT"; writerState="DORMANT"
            reviewerState="DORMANT"; builderState="DORMANT"; statusLine="CALM / SYSTEM HEALTHY"
        }
        function transfer(from, to) { transferFrom=from; transferTo=to; transferProgress=0; transferActive=true }
        function demoIdle() { scenario="IDLE"; reset() }
        function demoThinking() { scenario="THINKING"; reset(); coreState="THINKING"; missionStage=2; statusLine="THINKING / INPUT SYNTHESIS" }
        function demoWaiting() { scenario="WAITING"; reset(); coreState="WAITING_FOR_APPROVAL"; missionStage=3; researchState="WAITING"; writerState="WAITING"; reviewerState="WAITING"; statusLine="WAITING / USER APPROVAL REQUIRED" }
        function demoSpeaking() { scenario="SPEAKING"; reset(); coreState="SPEAKING"; missionStage=5; statusLine="SPEAKING / CONTROLLED OUTWARD WAVE" }
        function demoError() { scenario="ERROR"; reset(); coreState="ERROR"; statusLine="ERROR / CONTAINED DISCONTINUITY" }
        function start(name) { scenario=name; reset(); coreState="ATTENTION"; statusLine="ATTENTION / MOTION PROTOTYPE"; sequence.restart() }
        function advance() {
            phase += 1
            if (scenario === "SINGLE") {
                if (phase===1) { coreState="THINKING"; missionStage=1; statusLine="THINKING / RESEARCH REQUEST" }
                else if (phase===2) { coreState="PLANNING"; missionStage=2; researchState="AWAKENING"; statusLine="PLANNING / RESEARCH SELECTED" }
                else if (phase===3) { coreState="WAITING_FOR_APPROVAL"; missionStage=3; researchState="WAITING"; statusLine="WAITING / MOCK APPROVAL" }
                else if (phase===4) { coreState="EXECUTING"; missionStage=4; researchState="RECEIVING"; transfer("CORE","RESEARCH"); statusLine="TRANSFER / CORE TO RESEARCH" }
                else if (phase===5) { researchState="ACTIVE"; statusLine="ACTIVE / RESEARCHING LITERATURE" }
                else if (phase===6) { researchState="COMPLETED"; transfer("RESEARCH","CORE"); statusLine="RETURNING / RESEARCH RESULT" }
                else if (phase===7) { coreState="COMPLETED"; missionStage=6; statusLine="SUCCESS / RESULT CONVERGED" }
                else { demoIdle(); sequence.stop() }
            } else if (scenario === "SEQUENTIAL") {
                if (phase===1) { coreState="PLANNING"; missionStage=2; researchState="AWAKENING"; statusLine="PLANNING / FOUR-AGENT MISSION" }
                else if (phase===2) { coreState="EXECUTING"; missionStage=4; researchState="RECEIVING"; transfer("CORE","RESEARCH"); statusLine="TRANSFER / CORE TO RESEARCH" }
                else if (phase===3) { researchState="ACTIVE"; statusLine="ACTIVE / RESEARCH" }
                else if (phase===4) { researchState="COMPLETED"; writerState="RECEIVING"; transfer("RESEARCH","WRITER"); statusLine="HANDOFF / RESEARCH TO WRITER" }
                else if (phase===5) { writerState="ACTIVE"; statusLine="ACTIVE / WRITER" }
                else if (phase===6) { writerState="COMPLETED"; reviewerState="VERIFYING"; transfer("WRITER","REVIEWER"); statusLine="HANDOFF / WRITER TO REVIEWER" }
                else if (phase===7) { reviewerState="ACTIVE"; statusLine="VERIFY / REVIEWER" }
                else if (phase===8) { reviewerState="COMPLETED"; builderState="RECEIVING"; transfer("REVIEWER","BUILDER"); statusLine="HANDOFF / REVIEWER TO BUILDER" }
                else if (phase===9) { builderState="ACTIVE"; statusLine="ACTIVE / BUILDER" }
                else if (phase===10) { builderState="COMPLETED"; coreState="ORCHESTRATING"; transfer("BUILDER","CORE"); statusLine="CONVERGENCE / BUILDER TO JARVIS" }
                else if (phase===11) { coreState="COMPLETED"; missionStage=6; statusLine="SUCCESS / MISSION COMPLETE" }
                else { demoIdle(); sequence.stop() }
            } else if (scenario === "PARALLEL") {
                if (phase===1) { coreState="PLANNING"; missionStage=2; researchState="AWAKENING"; citationState="AWAKENING"; statusLine="PLANNING / PARALLEL BRANCHES" }
                else if (phase===2) { coreState="ORCHESTRATING"; missionStage=4; researchState="ACTIVE"; citationState="ACTIVE"; transfer("CORE","RESEARCH"); statusLine="ORCHESTRATING / RESEARCH + CITATION" }
                else if (phase===3) { transfer("CORE","CITATION"); statusLine="ORCHESTRATING / PARALLEL TRANSFER" }
                else if (phase===4) { researchState="COMPLETED"; citationState="COMPLETED"; writerState="RECEIVING"; transfer("RESEARCH","WRITER"); statusLine="CONVERGENCE / BRANCHES TO WRITER" }
                else if (phase===5) { transfer("CITATION","WRITER"); writerState="ACTIVE"; statusLine="ACTIVE / WRITER SYNTHESIS" }
                else if (phase===6) { writerState="COMPLETED"; coreState="COMPLETED"; missionStage=6; transfer("WRITER","CORE"); statusLine="SUCCESS / PARALLEL SYNTHESIS COMPLETE" }
                else { demoIdle(); sequence.stop() }
            }
        }
    }
    Timer { interval: 40; running: true; repeat: true; onTriggered: { motion.clock += .04; if (motion.transferActive) { motion.transferProgress += motion.reducedMotion ? .025 : .045; if (motion.transferProgress >= 1) motion.transferActive=false } } }
    Timer { id: sequence; interval: motion.reducedMotion ? 1600 : 1050; repeat: true; onTriggered: motion.advance() }

    component CutPanel: Item {
        property color fill: "#081324dc"; property color line: root.edge
        Canvas { anchors.fill: parent; onPaint: {
            var c=getContext("2d"); c.reset(); var cut=15;
            c.beginPath(); c.moveTo(cut,0); c.lineTo(width,0); c.lineTo(width,height-cut);
            c.lineTo(width-cut,height); c.lineTo(0,height); c.lineTo(0,cut); c.closePath();
            c.fillStyle=parent.fill; c.fill(); c.strokeStyle=parent.line; c.lineWidth=1; c.stroke();
            c.globalAlpha=.75; c.strokeStyle="#4da9d4"; c.beginPath(); c.moveTo(cut,5); c.lineTo(80,5); c.moveTo(width-5,height-70); c.lineTo(width-5,height-cut); c.lineTo(width-cut,height-5); c.stroke();
        }}
    }
    component MicroHeader: Label { color: "#8fb4d4"; font.pixelSize: 10; font.letterSpacing: 2; font.bold: true }
    component DataLine: Row { property string label: ""; property string value: ""; property color tone: "#87dfbb"; spacing: 7
        Label { text: "◆"; color: tone; font.pixelSize: 7; width: 8; anchors.verticalCenter: parent.verticalCenter }
        Label { text: label; color: root.muted; font.pixelSize: 10; width: 74 }
        Label { text: value; color: root.ink; font.pixelSize: 10; font.letterSpacing: .4 }
    }
    component AgentStone: Item {
        property string label: "AGENT"; property string glyph: "◇"; property color tone: root.cyan
        property string state: "DORMANT"; property bool active: state === "ACTIVE" || state === "VERIFYING"
        property bool primary: false
        property real energy: state === "DORMANT" ? .26 : (state === "WAITING" ? .46 : (state === "COMPLETED" ? .56 : 1))
        property real stateScale: state === "AWAKENING" || active || state === "RECEIVING" ? 1.13 : 1
        width: primary ? 106 : 90; height: primary ? 104 : 90
        scale: stateScale
        Behavior on scale { NumberAnimation { duration: motion.reducedMotion ? 0 : 500; easing.type: Easing.OutCubic } }
        Canvas { anchors.horizontalCenter: parent.horizontalCenter; width: primary ? 58 : 46; height: width; onPaint: {
            var c=getContext("2d"); c.reset(); var s=width, m=s/2;
            var aura=c.createRadialGradient(m,m,1,m,m,m); aura.addColorStop(0,parent.tone+(parent.energy>.8 ? "cc" : "66")); aura.addColorStop(.55,parent.tone+(parent.energy>.8 ? "55" : "18")); aura.addColorStop(1,"#00000000");
            c.fillStyle=aura; c.beginPath(); c.arc(m,m,m,0,6.283); c.fill();
            c.save(); c.translate(m,m); c.rotate(.785 + (parent.active && !motion.reducedMotion ? Math.sin(motion.clock*2)*.05 : 0)); c.fillStyle=parent.active ? parent.tone+"bb" : "#0c1a30"; c.strokeStyle=parent.tone; c.lineWidth=1.5;
            c.fillRect(-s*.25,-s*.25,s*.5,s*.5); c.strokeRect(-s*.25,-s*.25,s*.5,s*.5); c.restore();
            c.globalAlpha=.35+parent.energy*.5; c.strokeStyle=parent.tone; c.lineWidth=1; c.beginPath(); c.arc(m,m,s*.39,0,6.283); c.stroke();
        }}
        Label { anchors.horizontalCenter: parent.horizontalCenter; anchors.top: parent.top; anchors.topMargin: primary ? 12 : 15; text: glyph; color: tone; font.pixelSize: primary ? 21 : 17; font.bold: true }
        Label { anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; anchors.bottomMargin: 13; text: label; color: root.ink; font.pixelSize: 9; font.bold: true; font.letterSpacing: 1.2 }
        Label { anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; text: state; color: active ? "#ffd08a" : root.muted; font.pixelSize: 7; font.letterSpacing: .7 }
    }

    Canvas { anchors.fill: parent; onPaint: {
        var c=getContext("2d"); c.reset();
        var bg=c.createRadialGradient(width*.52,height*.47,20,width*.52,height*.47,width*.82); bg.addColorStop(0,"#112f54"); bg.addColorStop(.28,"#091b38"); bg.addColorStop(.62,"#040b1b"); bg.addColorStop(1,"#02040b"); c.fillStyle=bg; c.fillRect(0,0,width,height);
        var clouds=[[.16,.24,.25,"#224675"],[.83,.68,.28,"#253d70"],[.53,.11,.18,"#2a5a7c"]];
        for(var n=0;n<clouds.length;n++){var a=clouds[n],g=c.createRadialGradient(width*a[0],height*a[1],1,width*a[0],height*a[1],width*a[2]);g.addColorStop(0,a[3]+"55");g.addColorStop(1,"#00000000");c.fillStyle=g;c.fillRect(0,0,width,height);}
        c.globalAlpha=.58; for(var i=0;i<235;i++){var x=(i*97+31)%width,y=(i*53+17)%height,r=(i%19===0)?1.5:(i%7===0?1:.45);c.fillStyle=(i%17===0)?"#8bdfff":"#cbdcff";c.beginPath();c.arc(x,y,r,0,6.283);c.fill();}
        c.globalAlpha=.15; c.fillStyle="#86bfff"; for(var d=0;d<82;d++){var dx=(d*131)%width,dy=(d*79)%height;c.fillRect(dx,dy,(d%3)+1,1);}
        c.globalAlpha=.18; c.strokeStyle="#5796c8"; c.lineWidth=1; for(var k=0;k<3;k++){c.beginPath();c.ellipse(width*.52,height*.49,285+k*105,130+k*50,.12,3.55,5.95);c.stroke();} c.globalAlpha=1;
    }}

    header: Item { height: 65
        Rectangle { anchors.fill: parent; color: "#061122e8" }
        Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#315277" }
        RowLayout { anchors.fill: parent; anchors.leftMargin: 25; anchors.rightMargin: 25; spacing: 18
            Label { text: "JARVIS"; color: root.ink; font.pixelSize: 19; font.letterSpacing: 4; font.bold: true }
            Rectangle { width: 1; height: 24; color: "#365475" }
            Label { text: "SPACE–TIME INTELLIGENCE ENVIRONMENT"; color: root.muted; font.pixelSize: 10; font.letterSpacing: 2 }
            Item { Layout.fillWidth: true }
            Label { text: root.bridge ? "FUNCTIONAL HUD / REAL LOCAL STATE" : "VISUAL CONCEPT / MOCK STATE"; color: root.cyan; font.pixelSize: 10; font.bold: true; font.letterSpacing: 1.5 }
            Rectangle { width: 119; height: 27; color: "#0b2b42"; border.color: "#3d9bc3"; border.width: 1
                Label { anchors.centerIn: parent; text: "◆  STANDBY"; color: "#b8edff"; font.pixelSize: 10; font.bold: true; font.letterSpacing: 1 } }
        }
    }

    RowLayout { anchors.top: parent.top; anchors.topMargin: 83; anchors.bottom: parent.bottom; anchors.bottomMargin: 25; anchors.left: parent.left; anchors.right: parent.right; anchors.margins: 24; spacing: 20
        Item { Layout.preferredWidth: 258; Layout.fillHeight: true
            CutPanel { anchors.fill: parent }
            Column { anchors.fill: parent; anchors.margins: 19; spacing: 14
                MicroHeader { text: "COMMAND / HISTORY" }
                Rectangle { width: parent.width; height: 3; color: "#2d6b92" }
                Label { text: root.bridge ? "LIVE CONVERSATION" : "INCOMING MISSION"; color: root.muted; font.pixelSize: 9; font.letterSpacing: 1.4 }
                Label { text: root.bridge && root.bridge.messages.length ? root.bridge.messages[root.bridge.messages.length - 1].text : "Improve Chapter 3\nmethodology"; color: root.ink; font.pixelSize: 12; font.bold: true; width: parent.width; wrapMode: Text.WordWrap; maximumLineCount: 3 }
                Row { spacing: 8; Label { text:"◉"; color:root.liveCoreState === "ERROR" ? "#ff8290" : "#f4b96b"; font.pixelSize:10 } Label { text:root.bridge ? root.liveCoreState.replace("_", " ") : "AWAITING PLAN APPROVAL"; color:"#f6c480"; font.pixelSize:9; font.letterSpacing:1 } }
                Item { height: 9 }
                MicroHeader { text: "THESIS FIELD STATUS" }
                Repeater { model: root.bridge ? root.bridge.healthRows : [
                    {label:"THESIS",value:"ONLINE",tone:"#87dfbb"},{label:"CHAPTER",value:"03 / METHODOLOGY",tone:"#87bbff"},
                    {label:"RESEARCH",value:"CONTEXT READY",tone:"#70d8ff"},{label:"LATEX",value:"READY",tone:"#87dfbb"},
                    {label:"MEMORY",value:"ONLINE",tone:"#87dfbb"},{label:"VOICE",value:"UNQUALIFIED",tone:"#f4b96b"}]
                    delegate: DataLine { label:modelData.label; value:modelData.value; tone:modelData.tone } }
                Item { height: 7 }
                MicroHeader { text: "SIGNAL TRACE" }
                Repeater { model: root.bridge ? root.bridge.messages.slice(Math.max(0, root.bridge.messages.length - 3)) : ["Methodology context recovered","Literature route identified","Voice hardware deferred"]
                    delegate: Row { spacing:7; Label { text:"·"; color:"#4c9cc7"; font.pixelSize:18 } Label { text:typeof modelData === "string" ? modelData : (modelData.role + ": " + modelData.text); color:root.muted; font.pixelSize:10; width:195; wrapMode:Text.WordWrap; maximumLineCount:2 } } }
                Item { Layout.fillHeight: true }
                TextField { id: commandInput; visible: root.bridge; width:parent.width; placeholderText:"Ask JARVIS…"; onAccepted: { root.bridge.submitText(text); text="" } }
                Button { visible: root.bridge; width:parent.width; height:25; text:"SEND LOCAL REQUEST"; onClicked: { root.bridge.submitText(commandInput.text); commandInput.text="" } }
                Label { text:root.bridge ? "REAL CONVERSATION / LOCAL TEXT ONLY" : "STATIC DEVELOPMENT VISUAL"; color:"#52759a"; font.pixelSize:8; font.letterSpacing:1.1 }
            }
        }

        Item { id: field; Layout.fillWidth: true; Layout.fillHeight: true; clip: true
            Label { anchors.top: parent.top; anchors.horizontalCenter: parent.horizontalCenter; text:"JARVIS ORCHESTRATION FIELD"; color:"#91b7dc"; font.pixelSize:10; font.letterSpacing:2.5; font.bold:true }
            Label { anchors.top: parent.top; anchors.topMargin:18; anchors.horizontalCenter: parent.horizontalCenter; text:"GRAVITATIONAL INTELLIGENCE / STATIC CONCEPT"; color:"#55779d"; font.pixelSize:8; font.letterSpacing:1.4 }
            Canvas { anchors.fill: parent; onPaint: { var c=getContext("2d");c.reset();var x=width*.5,y=height*.45;
                c.globalAlpha=.34;c.strokeStyle="#4788bd";c.lineWidth=1; var paths=[[[.17,.2],[.33,.3],[.45,.4]],[[.84,.22],[.67,.32],[.55,.4]],[[.15,.72],[.32,.61],[.44,.5]],[[.83,.72],[.67,.61],[.56,.5]]];
                for(var i=0;i<paths.length;i++){var p=paths[i];c.beginPath();c.moveTo(width*p[0][0],height*p[0][1]);c.quadraticCurveTo(width*p[1][0],height*p[1][1],width*p[2][0],height*p[2][1]);c.stroke();}
                c.globalAlpha=.22;c.strokeStyle="#76d2f4"; for(var r=0;r<3;r++){c.beginPath();c.ellipse(x,y,168+r*60,62+r*28,-.24,0,6.283);c.stroke();}
                c.globalAlpha=.35;c.strokeStyle="#3d739e";c.beginPath();c.arc(x,y,280,.05,1.05);c.stroke();c.beginPath();c.arc(x,y,245,3.2,4.05);c.stroke(); c.globalAlpha=1;
            }}
            Canvas { id: core; anchors.centerIn: parent; anchors.verticalCenterOffset: -20; width: 590; height: 590
                rotation: motion.reducedMotion ? 0 : motion.clock * (root.liveCoreState === "THINKING" ? 8 : (root.liveCoreState === "ORCHESTRATING" ? 6 : (root.liveCoreState === "ERROR" ? -.8 : 1.2)))
                scale: root.liveCoreState === "THINKING" ? 1.045 : (root.liveCoreState === "EXECUTING" || root.liveCoreState === "SPEAKING" ? 1.03 : (root.liveCoreState === "ERROR" ? .96 : 1))
                Behavior on scale { NumberAnimation { duration: motion.reducedMotion ? 0 : 700; easing.type: Easing.InOutQuad } }
                onPaint: { var c=getContext("2d");c.reset();var x=width/2,y=height/2;
                var halo=c.createRadialGradient(x,y,5,x,y,238);halo.addColorStop(0,"#f0ffff");halo.addColorStop(.06,"#8de9ff");halo.addColorStop(.22,"#3f94ef99");halo.addColorStop(.53,"#1c4a9b30");halo.addColorStop(1,"#00000000");c.fillStyle=halo;c.beginPath();c.arc(x,y,238,0,6.283);c.fill();
                c.globalAlpha=.37;c.strokeStyle="#72bfff";c.lineWidth=1;for(var i=0;i<4;i++){c.beginPath();c.ellipse(x,y,132+i*32,50+i*16,(i-2)*.19,0,6.283);c.stroke();}
                c.globalAlpha=.8;c.strokeStyle="#9cefff";c.lineWidth=2;c.beginPath();c.ellipse(x,y,224,88,-.31,.18,5.8);c.stroke();c.strokeStyle="#5889e8";c.lineWidth=1;c.beginPath();c.ellipse(x,y,193,74,.45,1.1,5.95);c.stroke();
                var pts=[[x,y-162],[x+134,y-75],[x+148,y+80],[x,y+166],[x-145,y+72],[x-132,y-80]];c.globalAlpha=1;c.beginPath();c.moveTo(pts[0][0],pts[0][1]);for(var p=1;p<pts.length;p++)c.lineTo(pts[p][0],pts[p][1]);c.closePath();var face=c.createLinearGradient(x-150,y-160,x+150,y+165);face.addColorStop(0,"#b4f5ffcc");face.addColorStop(.3,"#477cddcc");face.addColorStop(.68,"#182f88cc");face.addColorStop(1,"#07113ccc");c.fillStyle=face;c.fill();c.strokeStyle="#b4f6ff";c.lineWidth=1.5;c.stroke();
                c.globalAlpha=.58;c.strokeStyle="#c0f5ff";c.beginPath();c.moveTo(x,y-162);c.lineTo(x,y+166);c.moveTo(x-132,y-80);c.lineTo(x+148,y+80);c.moveTo(x+134,y-75);c.lineTo(x-145,y+72);c.moveTo(x,y-162);c.lineTo(x+148,y+80);c.stroke();
                c.globalAlpha=1;var inner=c.createRadialGradient(x,y,3,x,y,78);inner.addColorStop(0,"#ffffff");inner.addColorStop(.13,"#c9ffff");inner.addColorStop(.37,"#55d9ff");inner.addColorStop(.7,"#285dc8cc");inner.addColorStop(1,"#10225f00");c.fillStyle=inner;c.beginPath();c.arc(x,y,80,0,6.283);c.fill();c.strokeStyle="#e5ffff";c.lineWidth=1.3;c.beginPath();c.moveTo(x,y-57);c.lineTo(x+52,y);c.lineTo(x,y+57);c.lineTo(x-52,y);c.closePath();c.stroke();
                c.globalAlpha=.9;c.strokeStyle="#b9fbff";c.lineWidth=2;c.beginPath();c.arc(x,y,109,4.0,5.28);c.stroke();c.strokeStyle="#4d9bff";c.beginPath();c.arc(x,y,128,.8,2.15);c.stroke();c.globalAlpha=1;
            }}
            Label { anchors.centerIn: core; anchors.verticalCenterOffset:-10; text:"◆"; color:"#f2ffff"; font.pixelSize:54; font.bold:true
                scale: motion.reducedMotion ? 1 : 1 + Math.sin(motion.clock * (root.liveCoreState === "THINKING" ? 6 : 2.2)) * (root.liveCoreState === "WAITING_FOR_APPROVAL" ? .018 : .075)
                opacity: root.liveCoreState === "DEGRADED" ? .55 : 1 }
            Label { anchors.horizontalCenter: parent.horizontalCenter; anchors.verticalCenter: parent.verticalCenter; anchors.verticalCenterOffset: 103; text:"JARVIS CORE"; color:root.ink; font.pixelSize:17; font.bold:true; font.letterSpacing:3 }
            Label { anchors.horizontalCenter: parent.horizontalCenter; anchors.verticalCenter: parent.verticalCenter; anchors.verticalCenterOffset: 128; text:root.liveCoreState.replace("_", " / "); color:root.liveCoreState === "ERROR" ? "#ff8c96" : root.cyan; font.pixelSize:9; font.letterSpacing:1.7 }
            AgentStone { x:field.width*(.17 + (motion.reducedMotion ? 0 : Math.sin(motion.clock*.22)*.012)); y:field.height*(.24 + (motion.reducedMotion ? 0 : Math.cos(motion.clock*.22)*.01)); label:"PLANNER"; glyph:"⌬"; tone:"#b185ff"; state:"DORMANT"; primary:true }
            AgentStone { x:field.width*(.70 + (motion.reducedMotion ? 0 : Math.sin(motion.clock*.19)*.012)); y:field.height*(.23 + (motion.reducedMotion ? 0 : Math.cos(motion.clock*.19)*.01)); label:"WRITER"; glyph:"✦"; tone:"#f3c765"; state:root.bridge ? root.bridge.agentState("writer") : motion.writerState; primary:true }
            AgentStone { x:field.width*(.15 + (motion.reducedMotion ? 0 : Math.sin(motion.clock*.25)*.012)); y:field.height*(.60 + (motion.reducedMotion ? 0 : Math.cos(motion.clock*.25)*.01)); label:"REVIEWER"; glyph:"◈"; tone:"#ff8290"; state:root.bridge ? root.bridge.agentState("reviewer") : motion.reviewerState; primary:true }
            AgentStone { x:field.width*(.72 + (motion.reducedMotion ? 0 : Math.sin(motion.clock*.18)*.012)); y:field.height*(.60 + (motion.reducedMotion ? 0 : Math.cos(motion.clock*.18)*.01)); label:"BUILDER"; glyph:"▣"; tone:"#ffac65"; state:root.bridge ? root.bridge.agentState("builder") : motion.builderState; primary:true }
            AgentStone { x:field.width*(.43 + (motion.reducedMotion ? 0 : Math.sin(motion.clock*.16)*.008)); y:field.height*(.06 + (motion.reducedMotion ? 0 : Math.cos(motion.clock*.16)*.008)); label:"RESEARCH"; glyph:"⌁"; tone:"#63baff"; state:root.bridge ? root.bridge.agentState("research") : motion.researchState }
            AgentStone { x:field.width*(.79 + (motion.reducedMotion ? 0 : Math.sin(motion.clock*.14)*.008)); y:field.height*(.44 + (motion.reducedMotion ? 0 : Math.cos(motion.clock*.14)*.008)); label:"CITATION"; glyph:"✧"; tone:"#7be0d0"; state:root.bridge ? root.bridge.agentState("citation") : motion.citationState }
            AgentStone { x:field.width*.43; y:field.height*.79; label:"MEMORY"; glyph:"◌"; tone:"#71d4a0"; state:"DORMANT" }
            AgentStone { x:field.width*.05; y:field.height*.45; label:"LATEX"; glyph:"⟐"; tone:"#91a6ff"; state:"DORMANT" }
            Canvas { id: transferLayer; anchors.fill: parent; z: 8
                function point(name) {
                    if (name === "CORE") return {x:width*.50,y:height*.45}
                    if (name === "RESEARCH") return {x:width*.48,y:height*.12}
                    if (name === "CITATION") return {x:width*.83,y:height*.49}
                    if (name === "WRITER") return {x:width*.76,y:height*.29}
                    if (name === "REVIEWER") return {x:width*.21,y:height*.66}
                    if (name === "BUILDER") return {x:width*.78,y:height*.66}
                    return {x:width*.50,y:height*.45}
                }
                onPaint: { var c=getContext("2d"); c.reset(); if (!motion.transferActive) return;
                    var a=point(motion.transferFrom), b=point(motion.transferTo), p=motion.transferProgress;
                    var cx=(a.x+b.x)/2+(a.y-b.y)*.13, cy=(a.y+b.y)/2+(b.x-a.x)*.12;
                    c.globalAlpha=.55; c.strokeStyle="#8be8ff"; c.lineWidth=1.4; c.beginPath();c.moveTo(a.x,a.y);c.quadraticCurveTo(cx,cy,b.x,b.y);c.stroke();
                    var q=1-p, px=q*q*a.x+2*q*p*cx+p*p*b.x, py=q*q*a.y+2*q*p*cy+p*p*b.y;
                    var glow=c.createRadialGradient(px,py,1,px,py,16);glow.addColorStop(0,"#ffffff");glow.addColorStop(.2,"#b8f7ff");glow.addColorStop(1,"#52bbff00");c.fillStyle=glow;c.beginPath();c.arc(px,py,16,0,6.283);c.fill();
                    c.fillStyle="#f1ffff";c.beginPath();c.arc(px,py,3.5,0,6.283);c.fill();c.globalAlpha=1;
                }
                Connections { target: motion; function onClockChanged() { transferLayer.requestPaint() } }
            }
            Item { anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; anchors.bottomMargin:2; width:Math.min(parent.width*.87,690); height:100
                Canvas { anchors.fill: parent; onPaint: { var c=getContext("2d");c.reset();c.globalAlpha=.52;c.strokeStyle="#3d8fc0";c.lineWidth=1.2;c.beginPath();c.moveTo(12,height*.65);c.bezierCurveTo(width*.23,3,width*.39,height,width*.57,height*.32);c.bezierCurveTo(width*.73,0,width*.85,height*.56,width-12,height*.38);c.stroke();c.globalAlpha=1; }}
                Label { anchors.top:parent.top; anchors.horizontalCenter:parent.horizontalCenter; text:"SPACE–TIME MISSION TRAJECTORY"; color:root.muted; font.pixelSize:9; font.letterSpacing:1.7 }
                Repeater { model:["REQUEST","UNDERSTAND","PLAN","APPROVE","EXECUTE","VERIFY","COMPLETE"]
                    delegate: Item { x: index*(parent.width-52)/6+15; y: index===3?43:(index%2?58:51); width:48;height:40
                        Rectangle { anchors.horizontalCenter:parent.horizontalCenter; width:index===root.liveMissionStage?13:8;height:width;radius:width/2;color:index<root.liveMissionStage?"#78cce5":(index===root.liveMissionStage?"#f6bd70":"#244562");border.color:index===root.liveMissionStage?"#ffe0a1":"#72a7c8";border.width:1 }
                        Label { anchors.top:parent.top; anchors.topMargin:17; anchors.horizontalCenter:parent.horizontalCenter; text:modelData; color:index===root.liveMissionStage?"#ffd394":root.ink;font.pixelSize:7; font.bold:index===root.liveMissionStage; font.letterSpacing:.5 }
                    } }
            }
        }

        Item { Layout.preferredWidth: 294; Layout.fillHeight: true
            CutPanel { anchors.fill: parent; fill:"#0a1425e8" }
            Column { anchors.fill: parent; anchors.margins: 19; spacing: 8
                MicroHeader { text:"MISSION / APPROVAL GATE" }
                Rectangle { width:parent.width; height:3; color:"#b77643" }
                Label { text:root.bridge ? (root.bridge.approval.status ? "REAL APPROVAL\nREQUEST" : "NO ACTIVE\nAPPROVAL") : "IMPROVE CHAPTER 3\nMETHODOLOGY"; color:root.ink; font.pixelSize:16; font.bold:true; lineHeight:1.12 }
                Rectangle { width:parent.width; height:32; color:"#38271f"; border.color:"#c4864b"; border.width:1
                    Label { anchors.centerIn:parent; text:root.bridge ? (root.bridge.approval.status || "◌  CONTROLLED / NO PENDING REQUEST") : "◉  WAITING FOR APPROVAL"; color:"#ffcf94"; font.pixelSize:10; font.bold:true; font.letterSpacing:1 } }
                MicroHeader { text:root.bridge ? "PROPOSAL DETAILS / REAL DATA" : "PROPOSED MISSION PLAN" }
                Repeater { model: root.bridge ? (root.bridge.approval.status ? [
                    ["ID",root.bridge.approval.proposal_id,"LIVE","#65cfff"],["SCOPE",root.bridge.approval.scope,"BOUND","#65cfff"],
                    ["OP",root.bridge.approval.operation,"REQUEST","#ffc36f"],["TARGET",root.bridge.approval.target,"LOCAL","#8297b8"]] : []) :
                    [["01","Research literature","COMPLETE","#65cfff"],["02","Draft methodology","COMPLETE","#65cfff"],["03","Reviewer evaluation","ACTIVE","#ffc36f"],["04","Apply approved changes","WAITING","#8297b8"],["05","Compile thesis","FUTURE","#576d8a"]]
                    delegate: Row { spacing:9; height:21
                        Label { text:modelData[0]; width:18;color:modelData[3];font.pixelSize:9;font.bold:true }
                        Label { text:modelData[1];width:151;color:root.ink;font.pixelSize:10 }
                        Label { text:modelData[2];color:modelData[3];font.pixelSize:8; font.letterSpacing:.5 }
                    } }
                Rectangle { width:parent.width; height:1;color:"#2c4868" }
                MicroHeader { text:root.bridge ? "SCOPED AUTONOMY / REAL STATE" : "ORCHESTRATION SIGNAL" }
                Label { text:root.bridge ? (root.bridge.autonomy.mode + "\n" + root.bridge.autonomy.scopes) : "RESEARCH  →  WRITER  →  REVIEWER\n                         ↓\n              BUILDER  →  JARVIS"; color:"#b9d8f0";font.pixelSize:10;lineHeight:1.35; width:parent.width; wrapMode:Text.WordWrap }
                Item { height:2 }
                Button { width:parent.width; height:29; text:root.bridge ? "APPROVE REAL REQUEST" : "APPROVE MOCK PLAN"; enabled:root.bridge ? !!root.bridge.approval.proposal_id : true; font.bold:true; onClicked: { if(root.bridge) root.bridge.approveProposal(root.bridge.approval.proposal_id); else motion.start("SEQUENTIAL") } }
                Button { visible:!root.bridge; height:visible ? 25 : 0; width:parent.width; text:"EDIT PLAN" }
                Button { width:parent.width; height:23; text:root.bridge ? "CANCEL REAL REQUEST" : "CANCEL"; onClicked: { if(root.bridge) root.bridge.cancelCurrent() } }
                Rectangle { visible:!root.bridge || root.bridge.prototypeMode; width:parent.width; height:visible ? 1 : 0; color:"#2c4868" }
                MicroHeader { visible:!root.bridge || root.bridge.prototypeMode; height:visible ? 12 : 0; text:"MOTION PROTOTYPE / DEVELOPMENT ONLY" }
                Grid { visible:!root.bridge || root.bridge.prototypeMode; height:visible ? implicitHeight : 0; columns:2; columnSpacing:6; rowSpacing:5; width:parent.width
                    Button { width:124; height:18; text:"IDLE"; onClicked: motion.demoIdle() }
                    Button { width:124; height:18; text:"THINKING"; onClicked: motion.demoThinking() }
                    Button { width:124; height:18; text:"WAIT APPROVAL"; onClicked: motion.demoWaiting() }
                    Button { width:124; height:18; text:"SINGLE AGENT"; onClicked: motion.start("SINGLE") }
                    Button { width:124; height:18; text:"SEQUENTIAL"; onClicked: motion.start("SEQUENTIAL") }
                    Button { width:124; height:18; text:"PARALLEL"; onClicked: motion.start("PARALLEL") }
                    Button { width:124; height:18; text:"SPEAKING"; onClicked: motion.demoSpeaking() }
                    Button { width:124; height:18; text:"COMPLETED"; onClicked: { motion.reset(); motion.coreState="COMPLETED"; motion.missionStage=6; motion.statusLine="SUCCESS / COMPLETED" } }
                    Button { width:124; height:18; text:"REDUCED MOTION"; checkable:true; checked:motion.reducedMotion; onClicked: motion.reducedMotion=checked }
                    Button { width:124; height:18; text:"ERROR"; onClicked: motion.demoError() }
                }
                Label { visible:!root.bridge || root.bridge.prototypeMode; height:visible ? 10 : 0; text:motion.statusLine; color:"#78c8ee"; font.pixelSize:8; font.letterSpacing:.7; width:parent.width; horizontalAlignment:Text.AlignHCenter }
                Item { Layout.fillHeight:true }
                Label { width:parent.width; text:root.bridge ? "REAL LOCAL PRESENTATION\nQML submits typed requests only." : "MOCK PRESENTATION ONLY\nNo authorization request is sent.";color:"#627b99";font.pixelSize:8;lineHeight:1.35; font.letterSpacing:.5 }
            }
        }
    }
}
