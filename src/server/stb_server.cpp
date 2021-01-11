#include "server/ClientsDatagramRouting.hpp"
#include "server/DatagramDispatcher.hpp"
#include "server/InitializationHandler.hpp"
#include "server/StatisticsSink.hpp"

#include "network.hpp"

#include <chrono> //TODO remove, just a temporary hack before handling signals
#include <memory>
#include <string>
#include <syslog.h>
#include <thread>

int main(int argc, char** argv) {
	// Parse command line
	//TODO
	uint16_t port = 3000;
	std::string game_summaries_path = "/tmp/stb_game_summaries.txt";
	syslog(LOG_INFO, "starting stb server, listening on port %d, logging games in '%s'", port, game_summaries_path.c_str());

	// Prepare components
	std::shared_ptr<ThreadSafeFifo<network::OutgoingUdpMessage>> out_messages(new ThreadSafeFifo<network::OutgoingUdpMessage>(5));
	std::shared_ptr<ThreadSafeFifo<network::IncommingUdpMessage>> in_messages(new ThreadSafeFifo<network::IncommingUdpMessage>(50));
	std::shared_ptr<ThreadSafeFifo<network::IncommingUdpMessage>> new_clients_queue(new ThreadSafeFifo<network::IncommingUdpMessage>(5));
	std::shared_ptr<ThreadSafeFifo<StatisticsSink::GameSummary>> statistics_event_queue(new ThreadSafeFifo<StatisticsSink::GameSummary>(5));
	std::shared_ptr<ClientsDatagramRouting> clients_queues(new ClientsDatagramRouting);

	network::SocketPool socket_pool;
	network::UdpOutput udp_sender(port, &socket_pool, out_messages.get());
	network::UdpInput udp_receiver(port, &socket_pool, in_messages.get());

	DatagramDispatcher dispatcher(in_messages, new_clients_queue, clients_queues);
	InitializationHandler initialization_handler(new_clients_queue, out_messages, clients_queues, statistics_event_queue);

	StatisticsSink statistics_sink(game_summaries_path, statistics_event_queue);

	// Start component threads
	std::thread udp_receiver_thread(&network::UdpInput::run, &udp_receiver);
	std::thread udp_sender_thread(&network::UdpOutput::run, &udp_sender);
	std::thread dispatcher_thread(&DatagramDispatcher::run, &dispatcher);
	std::thread initialization_handler_thread(&InitializationHandler::run, &initialization_handler);
	std::thread statistics_sink_thread(&StatisticsSink::run, &statistics_sink);
	syslog(LOG_INFO, "server ready");

	// Wait for known signal
	//TODO
	while (true) {
		std::this_thread::sleep_for(std::chrono::hours(1));
	}

	syslog(LOG_NOTICE, "server shutdown");
}
